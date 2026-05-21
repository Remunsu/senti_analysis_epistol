from django.urls import path
from rest_framework.routers import DefaultRouter
from .api import (
    SentimentAnalysisRunsView,
    SentimentAnalysisResultsView,
    SentimentAnalysisWorkFragmentsView,
    SentimentAnalysisView,
    SentimentAnnotationExportView,
    SentimentAnnotationSkipView,
    SentimentAnnotationTaskView,
    VolumeViewSet,
    WorkViewSet,
    XMLUploadView,
)

router = DefaultRouter()
router.register("volumes", VolumeViewSet)
router.register("works", WorkViewSet)

urlpatterns = [
    path("annotations/export/", SentimentAnnotationExportView.as_view()),
    path("annotations/skip/", SentimentAnnotationSkipView.as_view()),
    path("annotations/task/", SentimentAnnotationTaskView.as_view()),
    path("sentiment/analyze/", SentimentAnalysisView.as_view()),
    path("sentiment/runs/", SentimentAnalysisRunsView.as_view()),
    path("sentiment/results/", SentimentAnalysisResultsView.as_view()),
    path("sentiment/results/<int:run_id>/", SentimentAnalysisResultsView.as_view()),
    path(
        "sentiment/results/<int:run_id>/works/<int:original_work_id>/",
        SentimentAnalysisWorkFragmentsView.as_view(),
    ),
    path("upload/", XMLUploadView.as_view()),
]

urlpatterns += router.urls
