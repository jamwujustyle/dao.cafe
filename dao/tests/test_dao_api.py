from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework.test import APITestCase
from rest_framework import status

from django.core.files.uploadedfile import SimpleUploadedFile

from unittest.mock import patch
import tempfile
import os

from core.helpers.create_user import create_user

from .dao_utils import DaoBaseMixin, DaoFactoryMixin
from dao.models import Dao, Stake

from logging_config import logger


class DaoAPITests(APITestCase):
    # *NOTE: test Suite for dao api operations. involves testing dao api, appropriate status codes

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = create_user()
        cls.token = str(RefreshToken.for_user(cls.user).access_token)
        cls.HTTP_AUTHORIZATION = {f"HTTP_AUTHORIZATION": f"Bearer {cls.token}"}
        cls.url_prefix = "/api/v1/"

        cls.dao_base = DaoBaseMixin()

        dao_base = DaoBaseMixin()
        cls.dao_factory = DaoFactoryMixin()

        # *NOTE: TEST OBJECTS
        cls.dao = dao_base.create_dao(owner=cls.user)
        cls.dao1 = dao_base.create_dao(owner=cls.user, slug="newslugish")

        # *NOTE: CONFS
        cls.pagination_keys = ["count", "next", "previous", "results"]

    def test_dao_list_successfull(self):
        response = self.client.get(f"{self.url_prefix}dao/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data["data"]["results"]), 1)

    def test_dao_retrieval_successfull(self):
        response = self.client.get(f"{self.url_prefix}dao/slugish/info/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], "slugish")

    def test_dao_list_pagination(self):
        response = self.client.get(f"{self.url_prefix}dao/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key in self.pagination_keys:
            self.assertIn(key, response.data["data"])

    def test_dao_list_retrieves_empty_list(self):
        self.dao.delete()
        self.dao1.delete()
        response = self.client.get(f"{self.url_prefix}dao/")
        self.assertEqual([], response.data["data"]["results"])

    def test_dao_retrieval_dao_does_not_exist(self):
        response = self.client.get(f"{self.url_prefix}dao/nonexistent/info/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        with self.assertRaises(Dao.DoesNotExist):
            self.dao.refresh_from_db()

    def test_dao_unallowed_methods(self):
        response = self.client.post(f"{self.url_prefix}dao/", **self.HTTP_AUTHORIZATION)
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.put(
            f"{self.url_prefix}dao/slug/info/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.patch(
            f"{self.url_prefix}dao/slug/info/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        response = self.client.delete(
            f"{self.url_prefix}dao/slug/info/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    # *NOTE: DAO ENDPOINTS INTERACTING WITH BLOCKCHAIN

    @patch("services.blockchain.dao_service.DaoConfirmationService._get_initial_data")
    def test_dao_base_initialization(self, mock_get_initial_data):
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
            "network": 11155111,
        }

        payload = {
            "dao_address": dao_address,
            "network": 11155111,
        }

        response = self.client.post(
            f"{self.url_prefix}dao/fetch/", payload, **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch("services.blockchain.dao_service.DaoConfirmationService._get_initial_data")
    @patch("dao.packages.services.stake_service.StakeService.create_stake_instance")
    @patch("dao.packages.services.stake_service.StakeService.has_staked_amount")
    def test_dao_save_successful(
        self, mock_has_staked, mock_stake, mock_get_initial_data
    ):
        # Clear existing DAOs
        Dao.objects.all().delete()

        dao_address = "0x3CDCf8d0d3Ca5cDc423E4B5566554CC4a7Fc4830"

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
            "network": 11155111,
        }

        # First create the DAO through fetch endpoint
        fetch_payload = {
            "dao_address": dao_address,
            "network": 11155111,
        }
        fetch_response = self.client.post(
            f"{self.url_prefix}dao/fetch/", fetch_payload, **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(fetch_response.status_code, status.HTTP_201_CREATED)

        # Get the created DAO
        created_dao = Dao.objects.get(dao_contracts__dao_address=dao_address)

        # Create a stake for the user in the DAO (required for DAO save)
        Stake.objects.create(
            user=self.user,
            dao=created_dao,
            amount=10**18,  # 1 token with 18 decimals
            voting_power=10**18
        )

        mock_has_staked.return_value = True
        mock_stake.return_value = {
            "amount": 1,
            "voting_power": 1000000,
            "user": self.user,
            "dao": created_dao.id,
        }

        # Create a minimal valid JPEG image
        from PIL import Image
        import io
        
        # Create a small red image
        image = Image.new('RGB', (100, 100), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        payload = {
            "id": created_dao.id,
            "dao_image": SimpleUploadedFile(
                "media_file.jpg", image_io.read(), content_type="image/jpeg"
            ),
            "slug": "weirdo",
            "description": "brief",
        }

        response = self.client.patch(
            f"{self.url_prefix}dao/save/", payload, **self.HTTP_AUTHORIZATION
        )
        # Print response data for debugging
        print(f"Response data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], payload["slug"])

    # *NOTE: STAKE ENDPOINTS TIGHTLY ASSOCIATED WITH DAO. INTERACTION WITH BLOCKCHAIN TAKES PLACE

    def test_refresh_stake_retrieval_by_query_params(self):
        new_dao = self.dao_base.create_dao(slug="huyag")

        stake = Stake.objects.create(
            amount=1000000000000000000,
            voting_power=1000000000000000000,
            user=self.user,
            dao=new_dao,
        )

        self.assertIsNotNone(stake.id)

        response = self.client.get(
            f"{self.url_prefix}refresh/stake/", {"id": new_dao.id}
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount"], str(stake.amount))

        response = self.client.get(
            f"{self.url_prefix}refresh/stake/", {"slug": new_dao.slug}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["amount"], str(stake.amount))

    def test_refresh_stake_retrieval_stake_paginated(self):
        new_dao = self.dao_base.create_dao(slug="slug123")

        stake = Stake.objects.create(
            amount=1000000000000000000,
            voting_power=1000000000000000000,
            user=self.user,
            dao=new_dao,
        )

        response = self.client.get(f"{self.url_prefix}refresh/stake/", {"page": 1})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key in self.pagination_keys:
            self.assertIn(key, response.data["data"])
