from rest_framework import permissions

class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'staff'

class IsTeacherOrMentor(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['teacher', 'mentor', 'staff']

class IsStudentOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'staff':
            return True
        if hasattr(obj, 'student'):
            return obj.student.user == request.user
        return obj.user == request.user