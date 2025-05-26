from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model

from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status

from core.helpers.eth_address_generator import generate_test_eth_address
from logging_config import logger

User = get_user_model()


class UserAPITests(APITestCase):
    """
    test Suite for user API, checks jwt token

    Args:
        APITestCase (Class): django build in class
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = User.objects.create(
            eth_address=generate_test_eth_address(),
            nickname="user",
            email="johndoe@example.com",
        )
        cls.owner = User.objects.create(
            eth_address=generate_test_eth_address(), nickname="owner"
        )

        cls.user_token = str(RefreshToken.for_user(cls.user).access_token)
        cls.owner_token = str(RefreshToken.for_user(cls.owner).access_token)

        cls.HTTP_AUTHORIZATION = {"HTTP_AUTHORIZATION": f"Bearer {cls.user_token}"}
        cls.profile_url = "/api/v1/user/profile/"

    def test_user_retrieval_unautorized(self):
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_retrieval_successful(self):
        response = self.client.get(self.profile_url, **self.HTTP_AUTHORIZATION)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("eth_address", response.data)

        self.assertEqual(
            response.wsgi_request.META["HTTP_AUTHORIZATION"],
            f"Bearer {self.user_token}",
        )

    def test_user_patch_successful(self):
        mock_image = SimpleUploadedFile(
            "test_image.jpg", b"fake_image_data", content_type="image/jpeg"
        )
        response = self.client.patch(
            self.profile_url,
            email="johndoe@example.com",
            image=mock_image,
            **self.HTTP_AUTHORIZATION,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_user_patch_validation(self):
        response = self.client.patch(
            self.profile_url, {"email": "invalid @email"}, **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        mock_invalid_image = SimpleUploadedFile(
            "test.txt", b"not_an_image", content_type="text/plain"
        )

        response = self.client.patch(
            self.profile_url, {"image": mock_invalid_image}, **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_patch_unauthorized(self):
        response = self.client.patch(self.profile_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_partial_update(self):
        response = self.client.patch(
            self.profile_url, {"nickname": "test_nickname"}, **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nickname"], "test_nickname")

    def test_unsipported_methods(self):

        response = self.client.post(self.profile_url, **self.HTTP_AUTHORIZATION)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.put(self.profile_url, **self.HTTP_AUTHORIZATION)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(self.profile_url, **self.HTTP_AUTHORIZATION)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
