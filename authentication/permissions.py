"""
Permission classes to check if a user is a job seeker, an employer, or an admin.
"""
from rest_framework import permissions


class IsJobSeeker(permissions.BasePermission):
    """
    Check if a user is a job seeker.
    """
    def has_permission(self, request, view):
        """
        Returns True if the user is authenticated and has the role 'jobseeker', False otherwise.
        """
        return request.user.is_authenticated and request.user.role == 'jobseeker'


class IsEmployer(permissions.BasePermission):
    """
    Check if a user is an employer.
    """
    def has_permission(self, request, view):
        """
        Returns True if the user is authenticated and has the role 'employer', False otherwise.
        """
        return request.user.is_authenticated and request.user.role == 'employer'


class IsAdmin(permissions.BasePermission):
    """
    Check if a user is an admin.
    """
    def has_permission(self, request, view):
        """
        Returns True if the user is authenticated and is a staff user, False otherwise.
        """
        return request.user.is_authenticated and request.user.is_staff
