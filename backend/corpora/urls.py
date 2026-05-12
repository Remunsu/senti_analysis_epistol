from django.urls import path
from rest_framework.routers import DefaultRouter
from .api import (
    SentimentAnalysisResultsView,
    SentimentAnalysisView,
    SentimentAnnotationTaskView,
    VolumeViewSet,
    WorkViewSet,
    XMLUploadView,
)

router = DefaultRouter()
router.register("volumes", VolumeViewSet)
router.register("works", WorkViewSet)

urlpatterns = [
    path("annotations/task/", SentimentAnnotationTaskView.as_view()),
    path("sentiment/analyze/", SentimentAnalysisView.as_view()),
    path("sentiment/results/", SentimentAnalysisResultsView.as_view()),
    path("sentiment/results/<int:run_id>/", SentimentAnalysisResultsView.as_view()),
    path("upload/", XMLUploadView.as_view()),
]

urlpatterns += router.urls
