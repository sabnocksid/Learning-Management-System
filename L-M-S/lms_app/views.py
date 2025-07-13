from rest_framework import viewsets, generics, permissions, status
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.http import FileResponse, HttpResponseForbidden
from django.conf import settings
from drf_spectacular.utils import extend_schema, extend_schema_view
import os
import tempfile

from cryptography.fernet import Fernet
from django.http import StreamingHttpResponse, HttpResponseForbidden
from django.conf import settings
from utils.encryption import derive_key_from_user
import os

from .models import User, Course, Module, StudentProgress
from .serializers import (
    RegisterSerializer, NormalUserRegisterSerializer, AdminRegisterSerializer,
    CourseSerializer, ModuleSerializer, StudentProgressSerializer,
    CustomTokenObtainPairSerializer, EncryptedVideoUploadSerializer
)
from .permissions import IsStudentOrAdmin, IsProviderOrAdmin
from rest_framework_simplejwt.views import TokenObtainPairView
from utils.encryption import encrypt_file_for_user
from rest_framework.exceptions import ValidationError


@extend_schema(tags=['Authentication'])
class NormalUserRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = NormalUserRegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=['Authentication'])
class AdminRegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = AdminRegisterSerializer
    permission_classes = [permissions.IsAdminUser]


@extend_schema(tags=['Authentication'])
class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


@extend_schema_view(
    list=extend_schema(tags=['Courses']),
    retrieve=extend_schema(tags=['Courses']),
    create=extend_schema(tags=['Courses']),
    update=extend_schema(tags=['Courses']),
    partial_update=extend_schema(tags=['Courses']),
    destroy=extend_schema(tags=['Courses']),
)
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated, IsProviderOrAdmin]


@extend_schema_view(
    list=extend_schema(tags=['Modules']),
    retrieve=extend_schema(tags=['Modules']),
    create=extend_schema(tags=['Modules']),
    update=extend_schema(tags=['Modules']),
    partial_update=extend_schema(tags=['Modules']),
    destroy=extend_schema(tags=['Modules']),
)
class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsProviderOrAdmin]


@extend_schema_view(
    list=extend_schema(tags=['Student Progress']),
    retrieve=extend_schema(tags=['Student Progress']),
    create=extend_schema(tags=['Student Progress']),
    update=extend_schema(tags=['Student Progress']),
    partial_update=extend_schema(tags=['Student Progress']),
    destroy=extend_schema(tags=['Student Progress']),
)
class StudentProgressViewSet(viewsets.ModelViewSet):
    queryset = StudentProgress.objects.all()
    serializer_class = StudentProgressSerializer
    permission_classes = [permissions.IsAuthenticated, IsStudentOrAdmin]

    def perform_create(self, serializer):
        student = self.request.user
        module = serializer.validated_data.get('module')
        if StudentProgress.objects.filter(student=student, module=module).exists():
            raise ValidationError("Progress for this module already exists.")
        serializer.save(student=student)


@extend_schema(tags=['Secure Video'])
class EncryptedVideoUploadView(generics.GenericAPIView):
    serializer_class = EncryptedVideoUploadSerializer
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [permissions.IsAuthenticated, IsProviderOrAdmin]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course = serializer.validated_data['course']  # Already a Course instance
        title = serializer.validated_data['title']
        video_file = serializer.validated_data['video_file']

        with tempfile.NamedTemporaryFile(delete=False) as temp_input:
            for chunk in video_file.chunks():
                temp_input.write(chunk)
            temp_input_path = temp_input.name

        encrypted_filename = f"encrypted_{video_file.name}"
        encrypted_dir = os.path.join(settings.MEDIA_ROOT, 'encrypted_videos')
        os.makedirs(encrypted_dir, exist_ok=True)
        encrypted_path = os.path.join(encrypted_dir, encrypted_filename)

        try:
            encrypt_file_for_user(request.user, temp_input_path, encrypted_path)
        finally:
            os.remove(temp_input_path)

        module = Module.objects.create(
            course=course,
            title=title,
            video_file=f'encrypted_videos/{encrypted_filename}'
        )
        module_serializer = ModuleSerializer(module)
        return Response(module_serializer.data, status=status.HTTP_201_CREATED)


@extend_schema(tags=['Secure Video'])
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def serve_encrypted_video(request, filename):
    print(f"User: {request.user}")
    print(f"Auth: {request.META.get('HTTP_AUTHORIZATION')}")
    user = request.user
    if user.role not in ['student', 'admin']:
        return HttpResponseForbidden("Access denied.")


    file_path = os.path.join(settings.MEDIA_ROOT, 'encrypted_videos', filename)
    if not os.path.exists(file_path):
        return HttpResponseForbidden("Video not found or access denied.")

    return FileResponse(open(file_path, 'rb'), content_type='video/mp4')


from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from django.http import StreamingHttpResponse, HttpResponseForbidden
from cryptography.fernet import Fernet
import os

@extend_schema(
    tags=["Secure Video"],
    description="Stream decrypted video file for authenticated student or admin users.",
    responses={200: 'video/mp4'},
)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stream_decrypted_video(request, filename):
    user = request.user
    if user.role not in ['student', 'admin']:
        return HttpResponseForbidden("Access denied.")

    encrypted_path = os.path.join(settings.MEDIA_ROOT, 'encrypted_videos', filename)
    if not os.path.exists(encrypted_path):
        return HttpResponseForbidden("Video not found or access denied.")

    key = derive_key_from_user(user)
    cipher_suite = Fernet(key)

    def generator():
        with open(encrypted_path, 'rb') as f:
            encrypted_data = f.read()
            decrypted_data = cipher_suite.decrypt(encrypted_data)
            chunk_size = 8192
            for i in range(0, len(decrypted_data), chunk_size):
                yield decrypted_data[i:i + chunk_size]

    return StreamingHttpResponse(generator(), content_type='video/mp4')


