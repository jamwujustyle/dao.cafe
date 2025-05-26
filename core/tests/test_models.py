from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from datetime import datetime
from time import sleep
from unittest.mock import patch

from core.helpers.eth_address_generator import generate_test_eth_address
from core.validators.ethereum_validation import eth_regex
from core.models import User
from logging_config import logger


def create_user(
    eth_address="0x74fBBb0Be04653f29bd4b2601431E87f9B811340",
    password=None,
    email=None,
    **kwargs,
) -> User:
    """helper: create user with default eth-address (only field required)"""
    return get_user_model().objects.create_user(
        eth_address, password=password, email=email, **kwargs
    )


#####################  DATABASE AND CACHE LEVEL TESTS  ######################


class RedisCacheTests(TestCase):

    def test_cache_set_get(self):
        cache.set("test_key", "test_value", 30)
        self.assertEqual(cache.get("test_key"), "test_value")

    def test_cache_delete(self):
        cache.set("test_key_to_delete", "test_value")
        cache.delete("test_key_to_delete")
        self.assertIsNone(cache.get("test_key_to_delete"))

    def test_cache_with_wrong_value(self):
        cache.set(
            "test_key",
            "test_value",
        )
        stored_value = cache.get("test_key")
        wrong_value = "wrong_value"
        self.assertNotEqual(stored_value, wrong_value)

    def test_cache_expiration(
        self,
    ):
        cache.set("test_key", "test_key", timeout=1)
        sleep(1.1)
        result = cache.get("test_key", "no value found")

        self.assertEqual(result, "no value found")

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()


class ModelTests(
    TestCase,
):
    ################      TESTING USER/SUPERUSER CREATION      ######################

    def test_create_user_successful(self):
        """test user creation with eth-address successful"""
        user = create_user()
        self.assertIsNotNone(user)

    def test_create_superuser(self):
        """test superuser creation successful"""

        eth_address = generate_test_eth_address()
        user = get_user_model().objects.create_superuser(
            eth_address=eth_address,
            password="testpass123",
        )

        self.assertTrue(user.is_superuser)
        self.assertTrue(user.is_staff)
        # Ethereum addresses are now normalized to lowercase
        self.assertEqual(user.eth_address, eth_address.lower())

    """TESTING ETH ADDRESS VALID """

    def test_valid_eth_address(self):
        """test validate eth address format"""
        eth_address = generate_test_eth_address()

        # Ethereum addresses are now normalized to lowercase by the validator
        self.assertEqual(eth_regex(eth_address), eth_address.lower())

    def test_invalid_eth_address(self):
        """test invalid eth address not valid"""
        invalid_eth_address = "0x123"
        user = get_user_model().objects.create_user(eth_address=invalid_eth_address)
        with self.assertRaises(ValidationError):
            user.full_clean()

    """TESTING EMAIL"""

    def test_new_user_normalized_email(self):
        """test email is normalized when provided"""
        sample_emails = (
            ["test1@EXAMPLE.com", "test1@example.com"],
            ["Test2@Example.com", "Test2@example.com"],
            ["TEST3@EXAMPLE.COM", "TEST3@example.com"],
            ["test4@example.COM", "test4@example.com"],
        )
        for email, expected in sample_emails:

            user = create_user(
                eth_address=generate_test_eth_address(),
                email=email,
                password="sample123",
            )  # Pass eth_address implicitly
            self.assertEqual(user.email, expected)

    def test_new_user_with_no_email(self):
        """test user creation with missing email"""
        eth_address = generate_test_eth_address()
        user = get_user_model().objects.create_user(eth_address, email=None)
        self.assertIsNone(user.email)

    def test_invalid_email(self):
        """test invalid email format"""
        invalid_email = "not an email"
        user = create_user(email=invalid_email)
        with self.assertRaises(ValidationError):
            user.full_clean()

    """TESTING PASSWORD FOR SUPERUSERS"""

    def test_user_has_usable_password_even_without_password(self):
        """test user creation with password missing"""
        eth_address = generate_test_eth_address()
        user = get_user_model().objects.create_user(eth_address)

        self.assertFalse(user.has_usable_password())

    def test_superuser_with_no_password(self):
        """test superuser creation without password provided"""
        with self.assertRaises(ValueError):
            get_user_model().objects.create_superuser(
                eth_address=generate_test_eth_address(), password=None
            )

    """TEST USERS WITH NICKNAME"""

    def test_user_with_no_nickname(self):
        """test user creation when no nickname provided"""
        user = create_user(eth_address=generate_test_eth_address(), nickname=None)

        self.assertIsNone(user.nickname)

    def test_user_with_nickname(self):
        """test user creations when nickname is provided"""
        nickname = "testnick123"
        user = create_user(eth_address=generate_test_eth_address(), nickname=nickname)
        self.assertEqual(user.nickname, nickname)

    def test_invalid_nickname_format(self):
        """test invalid nickname format raises validation error"""
        invalid_nicknames = [
            "nickname!",
            "nick name",
            "@nickname",
            "nick#123",
        ]
        for nickname in invalid_nicknames:
            with self.assertRaises(ValidationError):
                create_user(
                    eth_address=generate_test_eth_address(),
                    nickname=nickname,
                ).full_clean()

    """TEST LAST SEEN AND DATE JOINED"""

    def test_date_joined_auto_set(self):
        """test date_joined is automatically set on creation"""
        user = create_user(eth_address=generate_test_eth_address())
        self.assertIsNotNone(user.date_joined)
        self.assertIsInstance(user.date_joined, datetime)

    def test_last_seen_auto_updates(self):
        """test last_seen updates on save"""
        user = create_user(eth_address=generate_test_eth_address())
        old_last_seen = user.last_seen

        sleep(0.1)
        user.save()
        self.assertGreater(user.last_seen, old_last_seen)

    #################   TODO: TEST ALL MODELS   #################
