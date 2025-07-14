from .models import Module, StudentProgress

def get_student_course_progress(student, course):
    total_modules = Module.objects.filter(course=course).count()
    if total_modules == 0:
        return 0
    completed_modules = StudentProgress.objects.filter(
        student=student,
        module__course=course,
        completed=True
    ).count()
    return round((completed_modules / total_modules) * 100, 2)