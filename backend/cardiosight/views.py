from pathlib import Path

from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .inference import CardioSightInference


model = CardioSightInference(
    media_root=settings.MEDIA_ROOT,
    weights_dir=settings.MODEL_WEIGHTS_DIR,
    pretrain_weights_dir=settings.PRETRAIN_WEIGHTS_DIR,
)


def clear_files(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    for file_path in directory.iterdir():
        if file_path.is_file():
            file_path.unlink()


class PatientFullFileList(APIView):
    def get(self, _request):
        base_path = settings.MEDIA_ROOT / "patients_data"
        if not base_path.exists():
            return Response([], status=status.HTTP_200_OK)

        folder_data = []
        for folder_path in sorted(base_path.iterdir()):
            if not folder_path.is_dir():
                continue
            file_names = sorted(path.name for path in folder_path.iterdir() if path.is_file())
            folder_data.append({"folder": folder_path.name, "files": file_names})

        return Response(folder_data, status=status.HTTP_200_OK)


class FileUploadView(APIView):
    def post(self, request, *args, **kwargs):
        image = request.FILES.get("image")
        hea = request.FILES.get("hea")
        dat = request.FILES.get("dat")
        hea_name = request.POST.get("hea_name") or (hea.name if hea else "")
        dat_name = request.POST.get("dat_name") or (dat.name if dat else "")

        if not image and not (hea and dat):
            return Response({"error": "파일 누락"}, status=status.HTTP_400_BAD_REQUEST)

        clear_files(settings.MEDIA_ROOT / "ecg_images")
        clear_files(settings.MEDIA_ROOT / "ecg_signals")
        clear_files(settings.MEDIA_ROOT / "xai_results")

        image_path = None
        signal_path = None

        if image:
            image_path = default_storage.save("ecg_images/img_sample", image)
        if hea and dat:
            signal_path = default_storage.save(f"ecg_signals/{hea_name}", hea)
            default_storage.save(f"ecg_signals/{dat_name}", dat)

        try:
            disease, info = model.predict()
        except Exception as exc:
            return Response(
                {"error": f"AI 분석 실패: {exc}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        xai_results = []
        if (settings.MEDIA_ROOT / "xai_results" / "img_xai.png").exists():
            xai_results.append("/media/xai_results/img_xai.png")
        if (settings.MEDIA_ROOT / "xai_results" / "sig_xai.png").exists():
            xai_results.append("/media/xai_results/sig_xai.png")

        return Response(
            {
                "disease": disease,
                "info": info,
                "image_url": f"/media/{image_path}" if image_path else None,
                "signal_url": f"/media/{signal_path}" if signal_path else None,
                "xai_results": xai_results,
            },
            status=status.HTTP_201_CREATED,
        )
