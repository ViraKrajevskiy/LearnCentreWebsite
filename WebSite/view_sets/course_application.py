"""
Заявка на курс: имя, Telegram, тег. Менеджеры обрабатывают после оплаты.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from WebSite.models.study.lesson import Course
from WebSite.models.course_application import CourseApplication


class CourseApplicationSubmitView(APIView):
    """POST: course_id, name, telegram, tag (опционально) — создаёт заявку на курс."""

    def post(self, request):
        course_id = request.data.get('course_id')
        name = (request.data.get('name') or '').strip()
        telegram = (request.data.get('telegram') or '').strip()
        tag = (request.data.get('tag') or '').strip()

        if not course_id:
            return Response(
                {'error': 'Укажите курс.', 'field': 'course_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not name:
            return Response(
                {'error': 'Укажите имя.', 'field': 'name'},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not telegram:
            return Response(
                {'error': 'Укажите Telegram.', 'field': 'telegram'},
                status=status.HTTP_400_BAD_REQUEST
            )

        course = Course.objects.filter(pk=course_id).first()
        if not course:
            return Response(
                {'error': 'Курс не найден.', 'field': 'course_id'},
                status=status.HTTP_400_BAD_REQUEST
            )

        student = None
        if request.user.is_authenticated and getattr(request.user, 'student', None):
            student = request.user.student

        CourseApplication.objects.create(
            course=course,
            student=student,
            name=name,
            telegram=telegram,
            tag=tag,
            status='pending',
        )
        return Response(
            {'success': True, 'message': 'Заявка отправлена. Менеджер свяжется с вами после оплаты.'},
            status=status.HTTP_201_CREATED
        )
