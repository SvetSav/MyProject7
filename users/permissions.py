from rest_framework.permissions import BasePermission


class IsModerator(BasePermission):
    """Пользователь входит в группу Moderators."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.groups.filter(name="Moderators").exists()
        )


class IsNotModerator(BasePermission):
    """Пользователь НЕ входит в группу Moderators."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and not request.user.groups.filter(name="Moderators").exists()
        )


class IsOwner(BasePermission):
    """Объект принадлежит текущему пользователю."""

    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user


class IsOwnerOrModerator(BasePermission):
    """Владелец объекта ИЛИ модератор."""

    def has_object_permission(self, request, view, obj):
        return (
            obj.owner == request.user
            or request.user.groups.filter(name="Moderators").exists()
        )


class IsOwnerOfProfile(BasePermission):
    """Объект — это профиль текущего пользователя."""

    def has_object_permission(self, request, view, obj):
        return obj == request.user
