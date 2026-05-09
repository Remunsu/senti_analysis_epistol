from rest_framework.routers import DefaultRouter
from .api import VolumeViewSet, WorkViewSet

router = DefaultRouter()
router.register("volumes", VolumeViewSet)
router.register("works", WorkViewSet)

urlpatterns = router.urls