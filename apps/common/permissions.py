from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """Allow reads to members, but mutations only to the object's owner."""

    owner_field = "author"

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, self.owner_field, None) or getattr(obj, "user", None)
        return owner == request.user
