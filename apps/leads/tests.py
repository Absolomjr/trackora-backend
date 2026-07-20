from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Lead
from .views import LeadRateThrottle

User = get_user_model()


class ThrottleControlMixin:
    """Pin the anon rate for a test case.

    DRF binds ``SimpleRateThrottle.THROTTLE_RATES`` as a class attribute at
    import time, so ``override_settings(REST_FRAMEWORK=...)`` has no effect on
    it. Patch the attribute directly instead, and clear the shared rate-limit
    cache so counts don't leak between tests.
    """

    throttle_rate = '1000/hour'

    def setUp(self):
        super().setUp()
        self._original_rates = LeadRateThrottle.THROTTLE_RATES
        LeadRateThrottle.THROTTLE_RATES = {'lead': self.throttle_rate}
        LeadRateThrottle().cache.clear()
        self.addCleanup(self._restore_rates)

    def _restore_rates(self):
        LeadRateThrottle.THROTTLE_RATES = self._original_rates
        LeadRateThrottle().cache.clear()


class LeadCreateTests(ThrottleControlMixin, APITestCase):
    url = '/api/leads/'

    def test_anonymous_can_submit_signup_lead(self):
        response = self.client.post(self.url, {
            'kind': 'signup',
            'full_name': 'Achieng Grace',
            'email': 'Grace@Kampala-Hardware.co.ug',
            'business_name': 'Kampala Hardware',
            'source': 'hero',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lead = Lead.objects.get()
        self.assertEqual(lead.kind, Lead.Kind.SIGNUP)
        self.assertEqual(lead.status, Lead.Status.NEW)
        # Email is normalised to lowercase.
        self.assertEqual(lead.email, 'grace@kampala-hardware.co.ug')

    def test_response_does_not_leak_the_stored_record(self):
        response = self.client.post(self.url, {
            'full_name': 'Okello Peter',
            'email': 'peter@example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(list(response.data.keys()), ['detail'])

    def test_request_metadata_is_captured_server_side(self):
        self.client.post(
            self.url,
            {'full_name': 'Nakato Sarah', 'email': 'sarah@example.com'},
            format='json',
            HTTP_USER_AGENT='Mozilla/5.0 (smoke-test)',
        )

        lead = Lead.objects.get()
        self.assertEqual(lead.user_agent, 'Mozilla/5.0 (smoke-test)')
        self.assertIsNotNone(lead.ip_address)

    def test_client_cannot_set_status_or_internal_note(self):
        self.client.post(self.url, {
            'full_name': 'Mugisha John',
            'email': 'john@example.com',
            'status': 'converted',
            'note': 'injected',
            'ip_address': '9.9.9.9',
        }, format='json')

        lead = Lead.objects.get()
        self.assertEqual(lead.status, Lead.Status.NEW)
        self.assertEqual(lead.note, '')
        self.assertNotEqual(lead.ip_address, '9.9.9.9')

    def test_demo_request_requires_a_way_to_reach_back(self):
        response = self.client.post(self.url, {
            'kind': 'demo',
            'full_name': 'Ssemakula Eric',
            'email': 'eric@example.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone', response.data)

    def test_demo_request_succeeds_with_a_phone_number(self):
        response = self.client.post(self.url, {
            'kind': 'demo',
            'full_name': 'Ssemakula Eric',
            'email': 'eric@example.com',
            'phone': '+256700000000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_missing_required_fields_are_rejected(self):
        response = self.client.post(self.url, {'full_name': 'X'}, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)
        self.assertIn('full_name', response.data)

    def test_link_spam_is_rejected(self):
        response = self.client.post(self.url, {
            'full_name': 'Spam Bot',
            'email': 'spam@example.com',
            'message': 'http://a.com http://b.com http://c.com',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('message', response.data)


class LeadThrottleTests(ThrottleControlMixin, APITestCase):
    url = '/api/leads/'
    throttle_rate = '2/hour'

    def test_anonymous_submissions_are_throttled(self):
        payload = {'full_name': 'Repeat Caller', 'email': 'repeat@example.com'}

        for _ in range(2):
            self.assertEqual(
                self.client.post(self.url, payload, format='json').status_code,
                status.HTTP_201_CREATED,
            )

        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class LeadAdminApiTests(ThrottleControlMixin, APITestCase):
    list_url = '/api/leads/all/'

    def setUp(self):
        super().setUp()
        self.lead = Lead.objects.create(full_name='Lead One', email='one@example.com')
        self.admin = User.objects.create_user(
            email='admin@trackora.test', password='pw', role=User.Role.ADMIN
        )
        self.staff = User.objects.create_user(
            email='staff@trackora.test', password='pw', role=User.Role.STAFF
        )

    def test_anonymous_cannot_list_leads(self):
        self.assertEqual(
            self.client.get(self.list_url).status_code, status.HTTP_401_UNAUTHORIZED
        )

    def test_staff_cannot_list_leads(self):
        self.client.force_authenticate(self.staff)
        self.assertEqual(
            self.client.get(self.list_url).status_code, status.HTTP_403_FORBIDDEN
        )

    def test_admin_can_list_leads(self):
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)

    def test_admin_can_update_status_but_not_contact_details(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f'{self.list_url}{self.lead.pk}/',
            {'status': 'contacted', 'note': 'Called on Monday', 'email': 'hacked@x.com'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.CONTACTED)
        self.assertEqual(self.lead.note, 'Called on Monday')
        self.assertEqual(self.lead.email, 'one@example.com')
