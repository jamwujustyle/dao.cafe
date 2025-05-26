from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch
import time

from django.contrib.auth import get_user_model
from django.core.cache import cache

from core.helpers.eth_address_generator import generate_test_eth_address
from eth_auth.eth_authentication import NonceManager
from logging_config import logger

User = get_user_model()


class EthAPITests(APITestCase):
    """
    test Suite for user API, checks jwt token

    Args:
        APITestCase (Class): django build in class
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eth_address = {"eth_address": generate_test_eth_address()}
        cls.nonce_url = "/api/v1/auth/nonce/"
        cls.verify_url = "/api/v1/auth/verify/"
        cls.payload = {
            **cls.eth_address,
            "signature": "0x" + "a" * 130,
            "message": "sign this message to verify ownership of eth_address",
        }
        cls.bad_payload = {
            "eth_address": generate_test_eth_address(),
            "signature": "invalid signature",
            "message": "invalid message",
        }

    def test_nonce_generation(self):
        response = self.client.post(self.nonce_url, self.eth_address)

        expected_keys = {"nonce", "timestamp"}

        self.assertTrue(expected_keys.issubset(response.data.keys()))

        self.assertTrue(isinstance(response.data["timestamp"], int))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_signature(self):

        with patch(
            "eth_auth.eth_authentication.SignatureVerifier.verify_ethereum_signature",
            return_value=True,
        ):
            response = self.client.post(self.verify_url, self.payload)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with patch(
            "eth_auth.eth_authentication.SignatureVerifier.verify_ethereum_signature",
            return_value=False,
        ):
            response = self.client.post(self.verify_url, self.payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_nonce(self):
        with patch(
            "eth_auth.eth_authentication.SignatureVerifier.verify_ethereum_signature",
            return_value=True,
        ):

            with patch("time.time", return_value=time.time()):
                self.client.post(self.nonce_url, self.eth_address)
            # FIXME: NEEDS TO BE CHANGED IN PRODUCTION ACCORDING TO THE CACJE TIMESPAN
            with patch("time.time", return_value=time.time() + 3601):
                response = self.client.post(self.verify_url, self.payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_verify_missing_nonce(self):
        response = self.client.post(self.verify_url, self.payload)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn(
            "invalid signature", str(response.data["error"]["non_field_errors"])
        )

    def test_malformed_eth_address(self):

        response = self.client.post(self.verify_url, self.bad_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_malformed_signature(self):
        nonce = "0995eec0693888d038356a45996cc7d1"
        timestamp = 1740303534
        cache_key = (
            f"{NonceManager.NONCE_PREFIX}{self.bad_payload['eth_address'].lower()}"
        )
        cache.set(cache_key, (nonce, timestamp))
        self.bad_payload["message"] = f"nonce: {nonce} timestamp: {timestamp}"

        with patch(
            "eth_auth.eth_authentication.NonceManager.verify_nonce", return_value=True
        ):
            with patch(
                "eth_auth.eth_authentication.SignatureVerifier.verify_ethereum_signature",
                return_value=False,
            ):
                response = self.client.post(self.verify_url, self.bad_payload)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(
                    "invalid signature", str(response.data["error"]["non_field_errors"])
                )
