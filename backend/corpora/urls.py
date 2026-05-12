from django.urls import path
from rest_framework.routers import DefaultRouter
from .api import SentimentAnnotationTaskView, VolumeViewSet, WorkViewSet, XMLUploadView

router = DefaultRouter()
router.register("volumes", VolumeViewSet)
router.register("works", WorkViewSet)

urlpatterns = [
    path("annotations/task/", SentimentAnnotationTaskView.as_view()),
    path("upload/", XMLUploadView.as_view()),
]

urlpatterns += router.urls
