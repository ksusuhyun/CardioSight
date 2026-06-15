from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import path

from cardiosight.views import FileUploadView, PatientFullFileList


def index(_request):
    return HttpResponse("CardioSight API server is running.")


urlpatterns = [
    path("", index),
    path("admin/", admin.site.urls),
    path("cardiosight/upload", FileUploadView.as_view()),
    path("cardiosight/patients_data/", PatientFullFileList.as_view()),
    # Backward-compatible aliases for the older ecg_web frontend.
    path("api/upload", FileUploadView.as_view()),
    path("api/patients_data/", PatientFullFileList.as_view()),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
