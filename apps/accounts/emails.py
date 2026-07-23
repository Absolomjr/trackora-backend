"""Transactional email helpers for the accounts app."""
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_password_reset_email(user):
    """Email a password-reset link to `user`.

    Uses Django's signed token generator (no extra model needed); the link is
    single-use and invalidated once the password changes or the token expires.
    """
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?uid={uid}&token={token}"

    subject = "Reset your Trackora password"
    body = (
        f"Hello {user.first_name or 'there'},\n\n"
        "We received a request to reset the password for your Trackora account.\n"
        "Click the link below to choose a new password. This link will expire "
        "and can only be used once:\n\n"
        f"{reset_url}\n\n"
        "If you didn't request this, you can safely ignore this email — your "
        "password won't change.\n\n"
        "— The Trackora team"
    )

    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
