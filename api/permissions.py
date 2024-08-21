from rest_framework.permissions import BasePermission

from api.models import PostFile


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.owner


class IsRelatedToThatUser(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user


class IsOwnerOfCurrentProject(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.project.owner == request.user


class CanInteractWithCurrentProject(BasePermission):
    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PostFile):
            obj = obj.post
        return obj.project.owner == request.user or \
            request.user in obj.project.participants.all()
