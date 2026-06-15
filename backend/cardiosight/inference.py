from glob import glob
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

from matplotlib import pyplot as plt
import numpy as np
from PIL import Image
import timm
import torch
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from torchvision import transforms
import wfdb

from .models import simple_multimodal
from .models import stmem_xai as stmem
from .utils.seed import seed
from .utils.sig_transform import (
    HighpassFilter,
    LowpassFilter,
    RandomCrop,
    Resample,
    Standardize,
)


class CardioSightInference:
    def __init__(self, media_root: Path, weights_dir: Path, pretrain_weights_dir: Path):
        self.media_root = Path(media_root)
        self.weights_dir = Path(weights_dir)
        self.pretrain_weights_dir = Path(pretrain_weights_dir)
        self.device = torch.device("cpu")
        self._load_models()

    def _load_models(self) -> None:
        self._require_file(self.weights_dir / "super_class_stmem.pth")
        self._require_file(self.weights_dir / "super_class_convnext.pth")
        self._require_file(self.weights_dir / "super_class_multi.pth")
        self._require_file(self.pretrain_weights_dir / "stmem_encoder.pth")

        self.sig_model = stmem.ST_MEM_ViT(
            seq_len=2250,
            patch_size=75,
            num_leads=12,
            num_classes=5,
            depth=12,
        )
        self.sig_model.load_state_dict(
            torch.load(self.weights_dir / "super_class_stmem.pth", map_location=self.device)
        )
        self.sig_model.to(self.device).eval()

        self.img_model = timm.create_model(
            "convnext_base",
            pretrained=False,
            num_classes=5,
            drop_path_rate=0.5,
        )
        self.img_model.load_state_dict(
            torch.load(self.weights_dir / "super_class_convnext.pth", map_location=self.device)
        )
        self.img_model.to(self.device).eval()

        self.multi_model = simple_multimodal.AveragewithProj(
            pretrain_path=self.pretrain_weights_dir / "stmem_encoder.pth",
            convnext_pretrained=False,
        )
        self.multi_model.load_state_dict(
            torch.load(self.weights_dir / "super_class_multi.pth", map_location=self.device)
        )
        self.multi_model.to(self.device).eval()

    @staticmethod
    def _require_file(path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Required model file is missing: {path}")

    def predict(self):
        seed(7)
        xai_dir = self.media_root / "xai_results"
        xai_dir.mkdir(parents=True, exist_ok=True)
        for file_path in xai_dir.iterdir():
            if file_path.is_file():
                file_path.unlink()

        img, ori_img, ori_shape = self._load_image()
        sig = self._load_signal()

        model_result = None
        if img is not None:
            model_result = self._run_image_model(img, ori_img, ori_shape, xai_dir)
        if sig is not None:
            model_result = self._run_signal_model(sig, xai_dir)
        if sig is not None and img is not None:
            model_result = self.multi_model(sig.to(torch.float32), img)[0]

        if model_result is None:
            raise ValueError("이미지 또는 신호 데이터를 읽을 수 없습니다.")

        model_result = torch.nn.functional.sigmoid(model_result.detach().cpu()).numpy()
        result = model_result >= 0.5
        return self._format_result(result, model_result)

    def _load_image(self):
        image_path = self.media_root / "ecg_images" / "img_sample"
        if not image_path.exists():
            return None, None, None

        crop_area = (0, 530, 2200, 1700 - 70)
        transform = transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.ToTensor(),
                transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
            ]
        )
        ori_img = Image.open(image_path).convert("RGB").crop(crop_area)
        ori_shape = np.array(ori_img).shape[:2]
        img = transform(ori_img).view(1, 3, 224, 224).to(self.device)
        return img, ori_img, ori_shape

    def _load_signal(self):
        hea_files = glob(str(self.media_root / "ecg_signals" / "*.hea"))
        if not hea_files:
            return None

        resample = Resample(target_fs=250)
        random_crop = RandomCrop(crop_length=2250)
        h_filter = HighpassFilter(fs=250, cutoff=0.67)
        l_filter = LowpassFilter(fs=250, cutoff=40)
        standardize = Standardize(axis=[-1, -2])

        sig, _ = wfdb.rdsamp(hea_files[0][:-4])
        sig = sig.T
        sig = resample(sig, 500)
        sig = random_crop(sig)
        sig = h_filter(sig)
        sig = l_filter(sig)
        sig = standardize([sig])[0]
        return torch.tensor(sig, dtype=torch.float).view(1, 12, -1).to(self.device)

    def _run_image_model(self, img, ori_img, ori_shape, xai_dir):
        model_result = self.img_model(img)[0]
        target_layers = [self.img_model.stages[-2]]
        targets = [ClassifierOutputTarget(int(model_result.argmax()))]

        with GradCAM(model=self.img_model, target_layers=target_layers) as cam:
            grayscale_cam = cam(input_tensor=img, targets=targets)[0, :]

        alpha = np.array(Image.fromarray(grayscale_cam).resize(ori_shape[::-1]))
        alpha_map = alpha * 0.6
        heatmap = plt.get_cmap("jet")(grayscale_cam)[:, :, :3]
        heatmap = (heatmap * 255).astype(np.uint8)
        heatmap = np.array(Image.fromarray(heatmap).resize(ori_shape[::-1])) / 255

        overlay = np.array(ori_img) / 255
        for channel in range(3):
            overlay[..., channel] = (
                heatmap[..., channel] * alpha_map
                + overlay[..., channel] * (1 - alpha_map)
            )
        overlay = np.clip(overlay, 0, 1)

        plt.imshow(overlay)
        plt.axis("off")
        plt.savefig(xai_dir / "img_xai.png", dpi=500, bbox_inches="tight", pad_inches=0)
        plt.close()
        return model_result

    def _run_signal_model(self, sig, xai_dir):
        attentions = []
        handles = []

        def save_attention(_module, _input, output):
            attentions.append(output[1].detach().cpu())

        try:
            for i in range(12):
                block = getattr(self.sig_model, f"block{i}").attn.fn
                handles.append(block.register_forward_hook(save_attention))

            model_result = self.sig_model(sig.to(torch.float32))[0]
            sig_idx = list((set(range(384)) - set(range(0, 384, 32))) - set(range(31, 384, 32)))
            att_map = [a[0].min(axis=0)[0] for a in attentions]
            att_map = [a + np.eye(a.shape[-1]) for a in att_map]
            att_map = [a / a.sum(-1, keepdims=True) for a in att_map]

            joint_attn = att_map[0]
            for attention in att_map[1:]:
                joint_attn = attention @ joint_attn

            rollup_result = joint_attn.mean(axis=0)[sig_idx]
            norm_rollup = (rollup_result - rollup_result.mean()) / rollup_result.std()
            ori_sig = sig[0].detach().cpu().numpy()
            self._save_signal_xai(ori_sig, norm_rollup, xai_dir)
            return model_result
        finally:
            for handle in handles:
                handle.remove()

    @staticmethod
    def _save_signal_xai(ori_sig, norm_rollup, xai_dir):
        cmap = plt.get_cmap("hot")
        lead_names = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]
        fig, axs = plt.subplots(6, 2, figsize=(16, 8))

        for i in range(12):
            col, row = divmod(i, 6)
            axs[row, col].set_title(f"Lead {lead_names[i]}", fontsize=12, pad=2)
            for j in range(30):
                axs[row, col].plot(
                    list(range(j * 75, j * 75 + 75)),
                    ori_sig[i][j * 75 : j * 75 + 75],
                    color=cmap(norm_rollup[i * 30 + j] - 1.4),
                    alpha=float(min(max(0, norm_rollup[i * 30 + j] - 1.2) + 0.2, 1)),
                    linewidth=3,
                )
            axs[row, col].set_xticks([])
            axs[row, col].set_yticks([])

        plt.tight_layout(pad=1)
        plt.savefig(xai_dir / "sig_xai.png", dpi=100, bbox_inches="tight")
        plt.close(fig)

    @staticmethod
    def _format_result(result, model_result):
        dis_list = [
            "Hypertrophy (심비대)",
            "Normal (정상)",
            "Myocardial Infarction (MI, 심근경색)",
            "Conduction Disturbance (전도 장애)",
            "ST/T Change (ST/T 변화)",
        ]
        info_list = [
            "심장 근육이 비정상적으로 두꺼워지거나, 심방·심실이 확장되어 심장이 커지는 질환입니다. 고혈압, 판막질환, 허혈성 심장질환 등 다양한 원인으로 발생하며, 초기에 증상이 없을 수 있지만 진행되면 호흡곤란, 흉통, 부종 등의 증상이 나타날 수 있습니다.",
            "오진 가능성에 대비하여, 강조된 영역이 임상적으로 유의한지 확인 바랍니다.",
            "관상동맥이 막혀 심장 근육 일부에 혈류가 차단되어 세포가 괴사하는 응급질환, 흔히 '심장마비'라고도 불립니다. 가슴 중앙이 쥐어짜는 듯한 통증, 숨 가쁨, 식은땀, 오심, 어지럼증, 피로",
            "심장의 전기 신호 전달에 이상이 생겨 박동이 느려지거나 불규칙해지는 질환입니다. 특별한 증상 없이 심전도로 발견되기도 하며, 심한 경우 어지럼증, 실신 등이 나타날 수 있습니다.",
            "심전도에서 ST분절이나 T파의 비정상적인 변화를 말하며, 특정 질병명은 아니며 여러 심장질환의 진단 보조지표입니다. 증상은 원인(허혈성 심장질환, 전해질 이상 등)에 따라 다양. 대표적으로 급성 심근경색, 심근허혈, 약물, 전해질 장애 등에서 관찰",
        ]

        disease = ""
        info = ""
        for i in range(5):
            if result[i]:
                if sum(result) > 1 and i == 1:
                    continue
                disease += f"{dis_list[i]} : {model_result[i] * 100:.0f}%,  "
                info += info_list[i] + "\n\r"

        return disease, info
