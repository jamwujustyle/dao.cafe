from .eth_address_generator import generate_test_eth_address
from .nickname_generator import generate_random_nickname
from django.contrib.auth import get_user_model
from uuid import uuid4


def create_user():
    User = get_user_model()
    return User.objects.create(
        eth_address=generate_test_eth_address(),
        nickname=generate_random_nickname(),
        email=f"johndoe@example.com_{uuid4().hex[:4]}",
    )
