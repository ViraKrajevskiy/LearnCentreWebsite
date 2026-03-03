from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from WebSite.models.opt_model import UserOTP
from django.contrib.auth import get_user_model

User = get_user_model()


@override_settings(CELERY_TASK_EAGER_PROPAGATION=True)  # на случай celery
class RegistrationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.registration_url = reverse('api_register')
        self.verify_url = reverse('api_verify_otp')

    def test_registration_get_returns_fields_info(self):
        response = self.client.get(self.registration_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('fields', data)
        self.assertIn('first_name', data['fields'])
        self.assertIn('surname', data['fields'])
        self.assertIn('phone_number', data['fields'])
        self.assertIn('telegram_username', data['fields'])

    @patch('WebSite.utils.telegram_bot.send_otp_to_telegram')
    def test_registration_post_creates_user_with_guest_role(self, mock_send):
        mock_send.return_value = True

        payload = {
            'first_name': 'Иван',
            'surname': 'Иванов',
            'last_name': 'Иванович',
            'phone_number': '+79991234567',
            'telegram_username': 'ivanov_test',
            'password': 'SecurePass123!',
        }

        response = self.client.post(self.registration_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertIn('session_id', data)
        self.assertIn('message', data)

        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(phone_number='+79991234567')
        self.assertEqual(user.role, 'guest')
        self.assertEqual(user.first_name, 'Иван')
        self.assertEqual(user.surname, 'Иванов')
        self.assertEqual(user.last_name, 'Иванович')
        self.assertEqual(user.telegram_username, 'ivanov_test')
        self.assertFalse(user.is_active)

        mock_send.assert_called_once()

    @patch('WebSite.utils.telegram_bot.send_otp_to_telegram')
    def test_registration_post_creates_otp(self, mock_send):
        mock_send.return_value = True

        payload = {
            'first_name': 'Мария',
            'surname': 'Петрова',
            'phone_number': '+79997654321',
            'telegram_username': 'maria_tg',
            'password': 'Secret456!',
        }

        response = self.client.post(self.registration_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        session_id = response.json()['session_id']

        otp = UserOTP.objects.get(session_id=session_id)
        self.assertEqual(otp.identifier, '+79997654321')
        self.assertEqual(len(otp.code), 6)

    @patch('WebSite.utils.telegram_bot.send_otp_to_telegram')
    def test_registration_validation_requires_fields(self, mock_send):
        response = self.client.post(self.registration_url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post(self.registration_url, {
            'first_name': 'Иван',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('WebSite.utils.telegram_bot.send_otp_to_telegram')
    def test_registration_duplicate_phone_fails(self, mock_send):
        mock_send.return_value = True

        payload = {
            'first_name': 'Иван',
            'surname': 'Иванов',
            'phone_number': '+79991111111',
            'telegram_username': 'duplicate',
            'password': 'Pass123!',
        }

        self.client.post(self.registration_url, payload, format='json')
        response = self.client.post(self.registration_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.filter(phone_number='+79991111111').count(), 1)


@override_settings(CELERY_TASK_EAGER_PROPAGATION=True)
class VerifyOTPAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.verify_url = reverse('api_verify_otp')

    @patch('WebSite.utils.telegram_bot.send_otp_to_telegram')
    def test_verify_otp_activates_user_and_returns_tokens(self, mock_send):
        mock_send.return_value = True

        user = User.objects.create_user(
            email='+79991234567@learncentre.local',
            phone_number='+79991234567',
            first_name='Test',
            surname='User',
            password='testpass123',
            role='guest',
        )
        user.is_active = False
        user.save()

        otp = UserOTP.objects.create(
            identifier='+79991234567',
            code='123456',
        )

        response = self.client.post(self.verify_url, {
            'session_id': str(otp.session_id),
            'code': '123456',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn('access', data)
        self.assertIn('refresh', data)

        user.refresh_from_db()
        self.assertTrue(user.is_active)

        otp.refresh_from_db()
        self.assertTrue(otp.is_used)

    def test_verify_otp_invalid_code_returns_400(self):
        response = self.client.post(self.verify_url, {
            'session_id': '00000000-0000-0000-0000-000000000000',
            'code': '000000',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
