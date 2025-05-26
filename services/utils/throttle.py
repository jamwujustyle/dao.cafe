from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
import sys


def is_test():
    """Check if code is running during test execution"""
    return "test" in sys.argv or any("pytest" in arg for arg in sys.argv)


class UserBurstRateThrottle(UserRateThrottle):
    scope = "user_burst"

    def allow_request(self, request, view):
        if is_test():
            return True
        return super().allow_request(request, view)


class UserSustainedRateThrottle(UserRateThrottle):
    scope = "user_sustained"

    def allow_request(self, request, view):
        if is_test():
            return True
        return super().allow_request(request, view)


class AnonBurstRateThrottle(AnonRateThrottle):
    scope = "anon_burst"

    def allow_request(self, request, view):
        if is_test():
            return True
        return super().allow_request(request, view)


class AnonSustainedRateThrottle(AnonRateThrottle):
    scope = "anon_sustained"

    def allow_request(self, request, view):
        if is_test():
            return True
        return super().allow_request(request, view)
