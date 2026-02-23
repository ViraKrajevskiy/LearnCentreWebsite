from rest_framework import viewsets

from WebSite.models.student_model import Attendance
from WebSite.permissions.roles_permissions import IsTeacherOrMentor, IsStudentOwner


class AttendanceViewSet(viewsets.ModelViewSet):
    queryset = Attendance.objects.all()

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
             permission_classes = [IsTeacherOrMentor]
        else:
            permission_classes = [IsStudentOwner]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        user = self.request.user
        if user.role in ['teacher', 'mentor', 'staff']:
            return Attendance.objects.all()
        return Attendance.objects.filter(student__user=user)