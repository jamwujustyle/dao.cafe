from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status
from decimal import Decimal

from .dao_utils import DaoBaseMixin, DaoFactoryMixin, PresaleFactoryMixin
from core.helpers.create_user import create_user
from dao.models import Presale, PresaleTransaction, PresaleStatus, Dao
from unittest.mock import patch, MagicMock

from logging_config import logger


class PresaleAPITest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Create test user and get authentication token
        cls.user = create_user()
        cls.token = str(RefreshToken.for_user(cls.user).access_token)
        cls.HTTP_AUTHORIZATION = {f"HTTP_AUTHORIZATION": f"Bearer {cls.token}"}

        # Create base objects for testing
        cls.dao_base = DaoBaseMixin(owner=cls.user)
        cls.dao = cls.dao_base.create_dao(network=11155111)
        cls.presale_base = PresaleFactoryMixin(owner=cls.user)
        cls.presale = cls.presale_base.create_presale(cls.dao)

        # *NOTE: CONFS
        cls.url_prefix = "/api/v1/dao/presales/"
        cls.pagination_keys = ["count", "next", "previous", "results"]

    # def tearDown(self):
    #     Dao.objects.all().delete()
    #     Presale.objects.all().delete()
    #     super().tearDown()

    def test_presales_returns_empty_list(self):
        """Test that presales endpoint returns an empty list when no presales match the query"""
        self.presale.delete()
        response = self.client.get(self.url_prefix, {"slug": f"{self.dao_base.slug}"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["results"], [])
        self.assertLessEqual(response.data["data"]["count"], 0)

    def test_presales_returns_paginated_response(self):
        """Test that presales endpoint returns a properly paginated response"""
        response = self.client.get(self.url_prefix)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        for key in self.pagination_keys:
            self.assertIn(key, response.data["data"])

    def test_dao_presales_returns_populated_list_successful(self):
        """Test listing presales for a specific DAO"""

        response = self.client.get(f"/api/v1/dao/{self.dao.slug}/presales/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data["data"]["results"]), 1)
        self.assertEqual(response.data["data"]["results"][0]["id"], self.presale.id)
        self.assertEqual(response.data["data"]["results"][0]["dao_slug"], self.dao.slug)

    def test_presale_detail(self):
        """Test retrieving a specific presale by ID"""
        response = self.client.get(f"{self.url_prefix}{self.presale.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.presale.id)
        self.assertEqual(
            response.data["presale_contract"], self.presale.presale_contract
        )
        self.assertEqual(response.data["status"], self.presale.status)

        self.assertEqual(
            response.data["total_token_amount"], str(self.presale.total_token_amount)
        )
        self.assertEqual(
            response.data["initial_price"], str(self.presale.initial_price)
        )

    def test_presale_not_found(self):
        response = self.client.get(f"{self.url_prefix}989899/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("error", response.data)

    @patch("dao.packages.services.presale_service.PresaleService.update_presale_state")
    @patch("dao.packages.services.presale_service.PresaleService.fetch_presale_events")
    def test_presale_refresh_successful(self, mock_fetch_events, mock_update_state):

        dao_factory = DaoFactoryMixin()

        dao = dao_factory.create_dao(slug="poppy", network=11155111)

        presale = Presale.objects.create(
            dao=dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        updated_presale = presale
        updated_presale.current_tier = 1
        updated_presale.current_price = Decimal("20")
        updated_presale.total_raised = Decimal("500")
        mock_update_state.return_value = updated_presale
        mock_fetch_events.return_value = []

        response = self.client.patch(
            f"{self.url_prefix}{presale.id}/refresh/", **self.HTTP_AUTHORIZATION
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["current_tier"], updated_presale.current_tier)
        self.assertEqual(response.data["current_price"], str(20))
        self.assertEqual(response.data["total_raised"], str(500))
        self

        mock_update_state.assert_called_once()
        mock_fetch_events.assert_called_once()

    @patch("dao.packages.services.presale_service.PresaleService.update_presale_state")
    def test_presale_refresh_failure(self, mock_update_state):
        dao_factory = DaoFactoryMixin()
        dao_with_contract = dao_factory.create_dao(slug="newslug", network=11155111)
        presale = Presale.objects.create(
            dao=dao_with_contract,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        mock_update_state.return_value = None

        response = self.client.patch(
            f"{self.url_prefix}{presale.id}/refresh/",
            **self.HTTP_AUTHORIZATION,
        )

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn("error", response.data)

    def test_presale_transactions_list(self):
        """Test listing transactions for a presale"""
        # Create test transactions
        for i in range(3):
            PresaleTransaction.objects.create(
                presale=self.presale,
                user=self.user,
                action=PresaleTransaction.ActionChoices.BUY,
                token_amount=Decimal("10"),
                eth_amount=Decimal("0.5"),
                block_number=1000 + i,
                transaction_hash=f"0x{i}234567890123456789012345678901234567890123456789012345678901234",
            )

        # Test the endpoint
        response = self.client.get(f"{self.url_prefix}{self.presale.id}/transactions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["results"]), 3)

        # Check transaction data
        transaction = response.data["data"]["results"][0]
        self.assertEqual(transaction["user_address"], self.user.eth_address)
        self.assertEqual(transaction["action"], PresaleTransaction.ActionChoices.BUY)
        self.assertEqual(transaction["token_amount"][:2], str(Decimal("10")))
        self.assertEqual(transaction["eth_amount"][:3], str(Decimal("0.5")))

    def test_presale_transactions_pagination(self):
        """Test that presale transactions are properly paginated"""
        # Create 15 test transactions (more than default page size)
        for i in range(15):
            if i < 10:
                tx_hash = f"0x{i}234567890123456789012345678901234567890123456789012345678901234"
            else:
                tx_hash = f"0x{i}23456789012345678901234567890123456789012345678901234567890123"
            PresaleTransaction.objects.create(
                presale=self.presale,
                user=self.user,
                action=PresaleTransaction.ActionChoices.BUY,
                token_amount=Decimal("10"),
                eth_amount=Decimal("0.5"),
                block_number=1000 + i,
                transaction_hash=tx_hash,
            )

        # Test first page
        response = self.client.get(
            f"{self.url_prefix}{self.presale.id}/transactions/",
            {"page": 1, "page_size": 10},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["results"]), 10)
        self.assertEqual(response.data["data"]["count"], 15)
        self.assertIsNotNone(response.data["data"]["next"])
        self.assertIsNone(response.data["data"]["previous"])
        # # Test second page
        response = self.client.get(
            f"{self.url_prefix}{self.presale.id}/transactions/",
            {"page": 2, "page_size": 10},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["results"]), 5)
        self.assertEqual(response.data["data"]["count"], 15)
        self.assertIsNone(response.data["data"]["next"])
        self.assertIsNotNone(response.data["data"]["previous"])

    def test_presale_status_update(self):
        """Test that presale status is updated when total_remaining becomes zero"""
        test_dao = self.dao_base.create_dao(slug="statusdao", network=11155111)
        presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
            total_remaining=100,
        )

        self.assertEqual(presale.status, PresaleStatus.ACTIVE)

        presale.total_remaining = 0

        with patch(
            "dao.packages.services.presale_service.PresaleService.update_presale_state"
        ) as mock_update:

            def update_status(presale_instance):
                presale_instance.status = PresaleStatus.COMPLETED
                return presale_instance

            mock_update.side_effect = update_status

            dao_factory = DaoFactoryMixin()
            dao_with_contract = dao_factory.create_dao(slug="womin", network=11155111)
            presale.dao = dao_with_contract
            presale.save()

            response = self.client.patch(
                f"{self.url_prefix}{presale.id}/refresh/", **self.HTTP_AUTHORIZATION
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data["status"], PresaleStatus.COMPLETED)

    def test_presale_transactions_empty(self):
        """Test that an empty list is returned when a presale has no transactions"""
        test_dao = self.dao_base.create_dao(slug="emptydao", network=11155111)
        empty_presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        response = self.client.get(f"{self.url_prefix}{empty_presale.id}/transactions/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["results"]), 0)
        self.assertEqual(response.data["data"]["count"], 0)

    def test_presale_transactions_with_different_actions(self):
        """Test that both BUY and SELL transactions are properly returned"""
        PresaleTransaction.objects.create(
            presale=self.presale,
            user=self.user,
            action=PresaleTransaction.ActionChoices.BUY,
            token_amount=Decimal("10"),
            eth_amount=Decimal("0.5"),
            block_number=1000,
            transaction_hash="0x1234567890123456789012345678901234567890123456789012345678901234",
        )

        PresaleTransaction.objects.create(
            presale=self.presale,
            user=self.user,
            action=PresaleTransaction.ActionChoices.SELL,
            token_amount=Decimal("5"),
            eth_amount=Decimal("0.25"),
            block_number=1001,
            transaction_hash="0x2234567890123456789012345678901234567890123456789012345678901234",
        )

        response = self.client.get(f"{self.url_prefix}{self.presale.id}/transactions/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]["results"]), 2)

        actions = [tx["action"] for tx in response.data["data"]["results"]]
        self.assertIn(PresaleTransaction.ActionChoices.BUY, actions)
        self.assertIn(PresaleTransaction.ActionChoices.SELL, actions)

    @patch("dao.packages.services.presale_service.PresaleService.fetch_presale_events")
    def test_presale_refresh_with_new_transaction(self, mock_fetch_events):
        """Test that new transactions are processed during a presale refresh"""
        dao_factory = DaoFactoryMixin()
        dao_with_contract = dao_factory.create_dao(slug="newslug", network=11155111)
        presale = Presale.objects.create(
            dao=dao_with_contract,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        mock_transaction = PresaleTransaction(
            presale=presale,
            user=self.user,
            action=PresaleTransaction.ActionChoices.BUY,
            token_amount=Decimal("15"),
            eth_amount=Decimal("0.75"),
            block_number=2000,
            transaction_hash="0x3234567890123456789012345678901234567890123456789012345678901234",
        )

        mock_fetch_events.return_value = [mock_transaction]

        with patch(
            "dao.packages.services.presale_service.PresaleService.update_presale_state"
        ) as mock_update:
            mock_update.return_value = presale

            response = self.client.patch(
                f"{self.url_prefix}{presale.id}/refresh/", **self.HTTP_AUTHORIZATION
            )

            self.assertEqual(response.status_code, status.HTTP_200_OK)

            mock_fetch_events.assert_called_once_with(presale)

    def test_presale_with_invalid_contract(self):
        """Test handling of a presale with an invalid contract address"""
        test_dao = self.dao_base.create_dao(slug="invaliddao", network=11155111)
        invalid_presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="invalid_address",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        with patch(
            "dao.packages.services.presale_service.PresaleService.update_presale_state"
        ) as mock_update:
            mock_update.side_effect = Exception("Invalid contract address")

            dao_factory = DaoFactoryMixin()
            dao_with_contract = dao_factory.create_dao(slug="kaisa", network=11155111)
            invalid_presale.dao = dao_with_contract
            invalid_presale.save()

            # Call the refresh endpoint
            response = self.client.patch(
                f"{self.url_prefix}{invalid_presale.id}/refresh/",
                **self.HTTP_AUTHORIZATION,
            )

            self.assertEqual(
                response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            self.assertIn("error", response.data)

    def test_presale_refresh_authentication_required(self):
        """Test that authentication is required for presale refresh"""
        test_dao = self.dao_base.create_dao(slug="authdao", network=11155111)
        presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        response = self.client.patch(f"{self.url_prefix}{presale.id}/refresh/")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_presale_paused_status(self):
        """Test presale with PAUSED status"""
        test_dao = self.dao_base.create_dao(slug="pauseddao", network=11155111)
        paused_presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.PAUSED,
        )

        response = self.client.get(f"{self.url_prefix}{paused_presale.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], PresaleStatus.PAUSED)

    def test_presale_filter_by_status(self):
        """Test filtering presales by status"""
        # self.presale.delete()
        test_dao = self.dao_base.create_dao(slug="filterdao", network=11155111)

        active_presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="0x1234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.ACTIVE,
        )

        completed_presale = Presale.objects.create(
            dao=test_dao,
            presale_contract="0x2234567890123456789012345678901234567890",
            total_token_amount=1000,
            initial_price=10,
            status=PresaleStatus.COMPLETED,
        )

        response = self.client.get(f"/api/v1/dao/{test_dao.slug}/presales/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"]["results"][0]["status"], PresaleStatus.COMPLETED
        )
        self.assertEqual(
            response.data["data"]["results"][1]["status"], PresaleStatus.ACTIVE
        )
        self.assertEqual(
            response.data["data"]["results"][0]["status"], completed_presale.status
        )
        self.assertEqual(
            response.data["data"]["results"][1]["status"], active_presale.status
        )
        self.assertEqual(len(response.data["data"]["results"]), 2)

    def test_presale_invalid_transaction_hash(self):
        """Test handling of duplicate transaction hash"""

        tx = PresaleTransaction.objects.create(
            presale=self.presale,
            user=self.user,
            action=PresaleTransaction.ActionChoices.BUY,
            token_amount=Decimal("10"),
            eth_amount=Decimal("0.5"),
            block_number=1000,
            transaction_hash="0x1234567890123456789012345678901234567890123456789012345678901234",
        )

        with self.assertRaises(Exception):
            PresaleTransaction.objects.create(
                presale=self.presale,
                user=self.user,
                action=PresaleTransaction.ActionChoices.BUY,
                token_amount=Decimal("20"),
                eth_emount=Decimal("1.0"),
                block_number=1001,
                transaction_hash="0x1234567890123456789012345678901234567890123456789012345678901234",
            )
