from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

# The reset endpoints are throttled; give the tests headroom.
from apps.accounts.views import PasswordResetThrottle  # noqa: E402


class ThrottleControlMixin:
    def setUp(self):
        super().setUp()
        self._rates = PasswordResetThrottle.THROTTLE_RATES
        PasswordResetThrottle.THROTTLE_RATES = {'password_reset': '1000/hour'}
        PasswordResetThrottle().cache.clear()
        self.addCleanup(self._restore)

    def _restore(self):
        PasswordResetThrottle.THROTTLE_RATES = self._rates
        PasswordResetThrottle().cache.clear()


class PasswordResetRequestTests(ThrottleControlMixin, APITestCase):
    url = '/api/auth/password-reset/'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email='owner@shop.test', password='OldPass123!', first_name='Sarah'
        )

    def test_known_email_sends_a_reset_link(self):
        res = self.client.post(self.url, {'email': 'owner@shop.test'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('reset-password', mail.outbox[0].body)

    def test_unknown_email_returns_same_response_and_sends_nothing(self):
        res = self.client.post(self.url, {'email': 'nobody@shop.test'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_email_is_case_insensitive(self):
        res = self.client.post(self.url, {'email': 'OWNER@Shop.test'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

    def test_inactive_user_gets_no_email(self):
        self.user.is_active = False
        self.user.save()
        self.client.post(self.url, {'email': 'owner@shop.test'}, format='json')
        self.assertEqual(len(mail.outbox), 0)


class PasswordResetConfirmTests(ThrottleControlMixin, APITestCase):
    url = '/api/auth/password-reset/confirm/'

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(email='owner@shop.test', password='OldPass123!')
        self.uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        self.token = default_token_generator.make_token(self.user)

    def test_valid_token_resets_password(self):
        res = self.client.post(self.url, {
            'uid': self.uid,
            'token': self.token,
            'new_password': 'BrandNew456!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('BrandNew456!'))

    def test_invalid_token_is_rejected(self):
        res = self.client.post(self.url, {
            'uid': self.uid,
            'token': 'not-a-real-token',
            'new_password': 'BrandNew456!',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('OldPass123!'))

    def test_token_is_single_use(self):
        first = self.client.post(self.url, {
            'uid': self.uid, 'token': self.token, 'new_password': 'BrandNew456!',
        }, format='json')
        self.assertEqual(first.status_code, status.HTTP_200_OK)

        second = self.client.post(self.url, {
            'uid': self.uid, 'token': self.token, 'new_password': 'Another789!',
        }, format='json')
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)

    def test_weak_password_is_rejected(self):
        res = self.client.post(self.url, {
            'uid': self.uid, 'token': self.token, 'new_password': '123',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', res.data)
