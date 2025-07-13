from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    NormalUserRegisterView,
    AdminRegisterView,
    CustomLoginView,
    CourseViewSet,
    ModuleViewSet,
    StudentProgressViewSet,
    EncryptedVideoUploadView,
    serve_encrypted_video,
    stream_decrypted_video
)

from django.urls import re_path


router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'student-progress', StudentProgressViewSet, basename='studentprogress')

urlpatterns = [
    # Auth related
    path('auth/register/', NormalUserRegisterView.as_view(), name='normal-register'),
    path('auth/admin-register/', AdminRegisterView.as_view(), name='admin-register'),
    path('auth/login/', CustomLoginView.as_view(), name='login'),

    # Secure video upload & serve
    path('secure-video/upload/', EncryptedVideoUploadView.as_view(), name='encrypted-video-upload'),
    re_path(r'^secure-video/serve/(?P<filename>.+)$', serve_encrypted_video, name='secure-video-serve'),
    path('secure-video/stream/<str:filename>/', stream_decrypted_video, name='stream-decrypted-video'),



    # API ViewSets (CRUD)
    path('', include(router.urls)),
]
