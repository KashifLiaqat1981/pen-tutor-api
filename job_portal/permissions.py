# permissions.py
from rest_framework import permissions

class IsEmployerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow employers to create/edit jobs.
    """
    
    def has_permission(self, request, view):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for authenticated employers
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Make sure only the user who posted the job can update/delete it
        return obj.employer == request.user

class IsJobSeekerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow job seekers to apply for jobs and manage applications.
    """
    
    def has_permission(self, request, view):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for authenticated job seekers
        if request.user and request.user.is_authenticated:
            return hasattr(request.user, 'jobseeker_profile')
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Read permissions for any request
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions only for the owner of the object
        if hasattr(obj, 'applicant'):
            return obj.applicant.user == request.user
        elif hasattr(obj, 'job_seeker'):
            return obj.job_seeker.user == request.user
        
        return False

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True
        
        # Write permissions are only allowed to the owner of the object.
        return obj.user == request.user

class IsAdminOrEmployerOwner(permissions.BasePermission):
    """
    Permission for admin to manage all jobs, or employer to manage their own jobs.
    """
    
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            return request.user.is_staff or hasattr(request.user, 'employer_profile')
        return False
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        if hasattr(obj, 'employer'):
            return obj.employer.user == request.user
        
        return False

class IsAdminOrOwner(permissions.BasePermission):
    """
    Permission for admin or object owner.
    """
    
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff:
            return True
        
        # Check various owner relationships
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'applicant'):
            return obj.applicant.user == request.user
        elif hasattr(obj, 'job_seeker'):
            return obj.job_seeker.user == request.user
        elif hasattr(obj, 'employer'):
            return obj.employer.user == request.user
        
        return False