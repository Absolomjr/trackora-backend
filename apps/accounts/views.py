from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .emails import send_password_reset_email
from .models import User
from .permissions import IsAdmin
from .serializers import (
    ChangePasswordSerializer,
    CustomTokenObtainPairSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    UpdateProfileSerializer,
    UserSerializer,
)


class PasswordResetThrottle(AnonRateThrottle):
    scope = 'password_reset'


class RegisterView(generics.CreateAPIView):
    """
    Register a new user.

    Open for the very first user; afterwards only an Admin may create accounts
    (so roles can't be self-assigned by the public).
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def get_permissions(self):
        if User.objects.exists():
            return [IsAdmin()]
        return [permissions.AllowAny()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """POST email + password -> access/refresh tokens + user payload."""
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


class ProfileView(generics.RetrieveUpdateAPIView):
    """GET / PATCH the currently authenticated user's profile."""
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return UpdateProfileSerializer
        return UserSerializer


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({'detail': 'Password updated successfully.'})


class PasswordResetRequestView(APIView):
    """POST an email to receive a reset link. Public + throttled.

    Always returns the same 200 response whether or not the email is
    registered, so it can't be used to discover which emails have accounts.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        user = User.objects.filter(email__iexact=email, is_active=True).first()
        if user:
            send_password_reset_email(user)

        return Response(
            {'detail': 'If an account exists for that email, a reset link is on its way.'},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """POST uid + token + new_password to set a new password. Public + throttled."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetThrottle]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            uid = force_str(urlsafe_base64_decode(data['uid']))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is None or not default_token_generator.check_token(user, data['token']):
            return Response(
                {'detail': 'This reset link is invalid or has expired. Please request a new one.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(data['new_password'])
        user.save()
        return Response({'detail': 'Your password has been reset. You can now sign in.'})


class UserListCreateView(generics.ListCreateAPIView):
    """Admin-only: list all users / create a user with a role."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
    search_fields = ['email', 'first_name', 'last_name']
    filterset_fields = ['role', 'is_active']

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RegisterSerializer
        return UserSerializer


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Admin-only: retrieve / update / deactivate a specific user."""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdmin]
