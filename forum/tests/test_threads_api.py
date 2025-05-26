import json, copy
from uuid import uuid4
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APITestCase
from rest_framework import status

from django.utils.dateparse import parse_datetime
from core.helpers.create_user import create_user
from dao.tests.dao_utils import DaoFactoryMixin
from unittest.mock import patch
from .forum_utils import ThreadBaseMixin
from logging_config import logger


class ThreadAPITests(APITestCase):

    # *NOTE: test Suite for dao api operations. involves testing dao api, appropriate status codes and object ownership
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.dao_factory = DaoFactoryMixin()

        # *NOTE: OBJECT BLUEPRINTS
        cls.dao = cls.dao_factory.create_dao()
        cls.user = cls.dao.owner

        cls.thread_base = ThreadBaseMixin(dao=cls.dao, author=cls.user)
        cls.thread = cls.thread_base.create_thread()

        # *NOTE: CONFS
        cls.url_prefix = "/api/v1/dao/slugish/threads/"
        cls.token = RefreshToken.for_user(cls.user).access_token
        cls.HTTP_AUTHORIZATION = {"HTTP_AUTHORIZATION": f"Bearer {cls.token}"}
        cls.pagination_keys = ["count", "next", "previous", "results"]

        # *NOTE: PAYLOAD TO USE ACROSS THE TESTS
        cls.payload = {
            "content": {
                "root": {
                    "description": "proposal desc here",
                    "children": [],
                }
            },
            "title": "no title",
        }

    def test_threads_retrieves_empty_list_successful(self):
        self.thread.delete()
        response = self.client.get(self.url_prefix)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["results"], [])
        self.assertLessEqual(response.data["data"]["count"], sum([]) - 0x0 - 0o0 - 0b0)

    def test_threads_paginated_response(self):
        response = self.client.get(self.url_prefix)

        for key in self.pagination_keys:
            self.assertIn(key, response.data["data"])

    def test_single_thread_retrieval_increments_view_count(self):
        response = self.client.get(
            f"{self.url_prefix}{self.thread.id}/", **self.HTTP_AUTHORIZATION
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertGreaterEqual(response.data["views_count"], 0x1)

    def test_single_thread_retrieval_without_headers_successful(self):
        response = self.client.get(f"{self.url_prefix}{self.thread.id}/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertLessEqual(response.data["views_count"], 0x0)

        response_time = parse_datetime(response.data["created_at"])

        self.assertEqual(self.thread.created_at, response_time)

    def test_thread_post_successful(self):
        response = self.client.post(
            self.url_prefix,
            self.payload,
            format="json",
            **self.HTTP_AUTHORIZATION,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["content"], self.payload["content"])

    def test_thread_like_succesful(self):
        response = self.client.post(
            f"{self.url_prefix}{self.thread.id}/like/",
            format="json",
            **self.HTTP_AUTHORIZATION,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data, {"status": "liked"})

        response = self.client.post(
            f"{self.url_prefix}{self.thread.id}/like/",
            format="json",
            **self.HTTP_AUTHORIZATION,
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data,
            {
                "status": "unliked",
                "msg": f"removed like from: Thread {self.thread.id}",
            },
        )

    def test_retrieve_replies_returns_empty_list(self):
        response = self.client.get(f"{self.url_prefix}{self.thread.id}/replies/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertLessEqual(response.data["data"]["count"], sum([]) - 0x0 - 0b0 - 0o0)

    def test_replies_retrieve_paginatied_response(self):
        response = self.client.get(f"{self.url_prefix}{self.thread.id}/replies/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for key in self.pagination_keys:
            self.assertIn(key, response.data["data"])
            
    def test_replies_are_ordered_chronologically_oldest_to_newest(self):
        # Create multiple replies
        for i in range(3):
            response = self.client.post(
                f"{self.url_prefix}{self.thread.id}/replies/",
                self.payload,
                format="json",
                **self.HTTP_AUTHORIZATION,
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Get all replies
        response = self.client.get(f"{self.url_prefix}{self.thread.id}/replies/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check if replies are ordered by created_at in ascending order (oldest first)
        results = response.data["data"]["results"]
        if len(results) >= 2:  # Only check if we have at least 2 results
            for i in range(len(results) - 1):
                current_date = parse_datetime(results[i]["created_at"])
                next_date = parse_datetime(results[i + 1]["created_at"])
                self.assertLessEqual(current_date, next_date, 
                                    "Replies should be ordered from oldest to newest")

    def test_replies_post_successful(self):
        response = self.client.post(
            f"{self.url_prefix}{self.thread.id}/replies/",
            self.payload,
            format="json",
            **self.HTTP_AUTHORIZATION,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data["content"], self.payload["content"])

        response2 = self.client.get(
            f"{self.url_prefix}{self.thread.id}/replies/",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response2.data["data"]["results"][0]["content"], response.data["content"]
        )

    def test_like_reply_on_thread_is_successful(self):
        response_reply = self.client.post(
            f"{self.url_prefix}{self.thread.id}/replies/",
            self.payload,
            format="json",
            **self.HTTP_AUTHORIZATION,
        )
        self.assertEqual(response_reply.status_code, status.HTTP_201_CREATED)
        response_like = self.client.post(
            f"{self.url_prefix}{self.thread.id}/replies/{response_reply.data['id']}/like/",
            **self.HTTP_AUTHORIZATION,
        )

        self.assertEqual(response_like.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response_like.data, {"status": "liked"})

        response_unlike = self.client.post(
            f"{self.url_prefix}{self.thread.id}/replies/{response_reply.data['id']}/like/",
            **self.HTTP_AUTHORIZATION,
        )
        self.assertEqual(response_unlike.status_code, status.HTTP_200_OK)
        self.assertEqual(response_unlike.data["status"], "unliked")
