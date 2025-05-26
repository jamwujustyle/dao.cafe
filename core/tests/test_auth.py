from datetime import timedelta
from unittest.mock import patch, MagicMock

from rest_framework_simplejwt.tokens import RefreshToken, AccessToken, TokenError
from rest_framework import status

from django.test import TestCase, Client
from django.utils.timezone import now
from django.core.cache import cache

from core.helpers.create_user import create_user
from dao.models import Dao
from eth_auth.eth_authentication import NonceManager, SignatureVerifier
from logging_config import logger


class AuthenticationTests(TestCase):
    """
    test Suite for jwt token logic (expiration, validation, etc.)

    Args:
        APITestCase (Class): django build in class
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = Client()
        cls.user = create_user()
        # cls.owner = User.objects.create(
        #     eth_address=generate_test_eth_address(), nickname="owner"
        # )

        cls.user_token = str(RefreshToken.for_user(cls.user).access_token)
        # cls.owner_token = str(RefreshToken.for_user(cls.owner).access_token)

        cls.HTTP_AUTHORIZATION = {"HTTP_AUTHORIZATION": f"Bearer {cls.user_token}"}
        # cls.owner_headers = {"HTTP_AUTHORIZATION": f"Bearer {cls.owner}"}

        cls.url_prefix = "/api/v1/"

    def test_expired_token(self):
        """Test that expired tokens are properly rejected"""
        token = AccessToken(self.user_token)

        try:
            token.verify()
            is_valid = True
        except TokenError:
            is_valid = False

        self.assertTrue(is_valid)

        past_timestamp = int((now() - timedelta(days=1)).timestamp())
        token.payload["exp"] = past_timestamp

        with self.assertRaises(TokenError):
            token.verify()

    def test_malformed_token(self):
        """Test that malformed tokens are properly rejected"""
        malformed_token_str = str(self.user_token) + "123123"

        with self.assertRaises(TokenError):
            AccessToken(malformed_token_str).verify()

    def test_login_with_no_jwt(self):
        """Test that endpoints requiring authentication reject requests without JWT"""
        response = self.client.post(f"{self.url_prefix}user/profile/", user=self.user)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn(
            "Authentication credentials were not provided", response.data["error"]
        )

    @patch("services.blockchain.dao_service.DaoConfirmationService._get_initial_data")
    def test_dao_base_initialization(self, mock_get_initial_data):
        """Test that DAO initialization requires authentication"""
        Dao.objects.all().delete()

        dao_address = "0x3CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4830"
        # Mock the blockchain response
        mock_get_initial_data.return_value = {
            "sender": self.user.eth_address,
            "dao_address": dao_address,
            "token_address": "0x4CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4831",
            "treasury_address": "0x5CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4832",
            "staking_address": "0x6CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4833",
            "dao_name": "Test DAO",
            "token_name": "Test Token",
            "version": "1.0.0",
            "symbol": "TEST",
            "total_supply": "1000000000000000000000000",
        }

        payload = {
            "dao_address": dao_address,
            "network": 11155111,
        }

        response = self.client.post(f"{self.url_prefix}dao/fetch/", payload)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Test that refresh tokens can be used to obtain new access tokens"""
        refresh = RefreshToken.for_user(self.user)

        payload = {"refresh": str(refresh)}

        response = self.client.post(
            f"{self.url_prefix}auth/refresh/",
            payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        new_token = response.data["access"]
        headers = {"HTTP_AUTHORIZATION": f"Bearer {new_token}"}

        profile_response = self.client.get(f"{self.url_prefix}user/profile/", **headers)
        self.assertNotEqual(profile_response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch("eth_auth.eth_authentication.NonceManager.generate_nonce")
    def test_nonce_generation(self, mock_generate_nonce):
        """Test the nonce generation endpoint"""
        mock_generate_nonce.return_value = "test_nonce"

        eth_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        payload = {"eth_address": eth_address}

        response = self.client.post(
            f"{self.url_prefix}auth/nonce/", payload, content_type="application/json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("nonce", response.data)
        self.assertIn("timestamp", response.data)
        mock_generate_nonce.assert_called_once_with(eth_address.lower())

    @patch("eth_auth.eth_authentication.SignatureVerifier.verify_ethereum_signature")
    @patch("eth_auth.eth_authentication.NonceManager.verify_nonce")
    def test_signature_verification(self, mock_verify_nonce, mock_verify_signature):
        """Test the signature verification endpoint"""
        mock_verify_nonce.return_value = True
        mock_verify_signature.return_value = True

        eth_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        signature = "0x1234567890abcdef"
        message = "Test message with nonce"

        nonce = "test_nonce"
        timestamp = int(now().timestamp())
        cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address.lower()}"
        cache.set(cache_key, (nonce, timestamp), timeout=3600)

        payload = {
            "eth_address": eth_address,
            "signature": signature,
            "message": message,
        }

        response = self.client.post(
            f"{self.url_prefix}auth/verify/",
            payload,
            content_type="application/json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertTrue(response.data["is_success"])

        mock_verify_nonce.assert_called_once_with(eth_address.lower(), nonce, delete_on_success=False)

        mock_verify_signature.assert_called_once_with(
            message=message, signature=signature, eth_address=eth_address.lower(), 
            stored_nonce=nonce, timestamp=timestamp
        )

    @patch("eth_auth.eth_authentication.SignatureVerifier.verify_ethereum_signature")
    def test_invalid_signature(self, mock_verify_signature):
        """Test that invalid signatures are properly rejected"""
        mock_verify_signature.return_value = False

        eth_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        signature = "0x1234567890abcdef"
        message = "Test message with nonce"

        nonce = "test_nonce"
        timestamp = int(now().timestamp())
        cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address.lower()}"
        cache.set(cache_key, (nonce, timestamp), timeout=3600)

        payload = {
            "eth_address": eth_address,
            "signature": signature,
            "message": message,
        }

        response = self.client.post(
            f"{self.url_prefix}auth/verify/", payload, content_type="application/json"
        )

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_eth_address(self):
        """Test that invalid Ethereum addresses are properly rejected"""
        invalid_eth_address = "0xinvalid"

        payload = {"eth_address": invalid_eth_address}

        response = self.client.post(
            f"{self.url_prefix}auth/nonce/", payload, content_type="application/json"
        )

        if response.status_code == 404:
            self.skipTest("Nonce endpoint not found at expected URL")

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_expired_nonce(self):
        """Test that expired nonces are properly rejected"""
        eth_address = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        signature = "0x1234567890abcdef"
        message = "Test message with nonce"

        nonce = "test_nonce"
        timestamp = int((now() - timedelta(days=1)).timestamp())
        cache_key = f"{NonceManager.NONCE_PREFIX}{eth_address.lower()}"
        cache.set(cache_key, (nonce, timestamp), timeout=3600)

        payload = {
            "eth_address": eth_address,
            "signature": signature,
            "message": message,
        }

        response = self.client.post(
            f"{self.url_prefix}auth/verify/", payload, content_type="application/json"
        )

        self.assertNotEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_request(self):
        """Test that authenticated requests are properly processed"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.user_token}"}

        response = self.client.get(f"{self.url_prefix}user/profile/", **headers)

        self.assertNotEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
