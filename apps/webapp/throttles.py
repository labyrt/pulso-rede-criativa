from rest_framework.throttling import UserRateThrottle


class AuthRateThrottle(UserRateThrottle):
    scope = "auth"


class PostRateThrottle(UserRateThrottle):
    scope = "post"


class AIRateThrottle(UserRateThrottle):
    scope = "ai"
