from django.core.exceptions import PermissionDenied
from .models import ProjectMember

class ProjectMemberRequiredMixin:
    """Миксин для проверки, что пользователь является участником проекта"""
    def dispatch(self, request, *args, **kwargs):
        project = self.get_object() if hasattr(self, 'get_object') else None
        if project and not ProjectMember.objects.filter(project=project, user=request.user).exists():
            raise PermissionDenied("Вы не являетесь участником этого проекта")
        return super().dispatch(request, *args, **kwargs)

class ProjectOwnerRequiredMixin:
    """Миксин для проверки, что пользователь является владельцем проекта"""
    def dispatch(self, request, *args, **kwargs):
        project = self.get_object() if hasattr(self, 'get_object') else None
        if project and not ProjectMember.objects.filter(
            project=project, 
            user=request.user,
            role__name='Owner'
        ).exists():
            raise PermissionDenied("Только владелец проекта может выполнять это действие")
        return super().dispatch(request, *args, **kwargs)