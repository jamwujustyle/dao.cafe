import randomname
from django.db.utils import ProgrammingError


def generate_random_nickname() -> str:
    name = randomname.get_name()

    if "-" in name:
        parts = name.split("-")
        formatted_name = "".join(part.capitalize() for part in parts)
        return formatted_name[:20]
    return name.capitalize()[:20]


def generate_unique_nickname():
    from core.models import User

    try:
        if not User.objects.exists():
            return generate_random_nickname()

        while True:
            nickname = generate_random_nickname()
            if not User.objects.filter(nickname=nickname).exists():
                return nickname
    except ProgrammingError:
        return generate_random_nickname()
