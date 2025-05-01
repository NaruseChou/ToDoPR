from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.views.generic.list import ListView
from django.http import HttpResponse
from django.db import connection
from django.shortcuts import render
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import Q
from .forms import PositionForm, TaskForm, ProjectForm, InviteForm
from .models import Task, Project, ProjectMember, Role
from django.contrib.auth.models import User
from django.shortcuts import redirect, get_object_or_404
from .forms import TaskForm, ProjectForm, InviteForm, PositionForm
from .mixins import ProjectOwnerRequiredMixin, ProjectMemberRequiredMixin

from .forms import PositionForm
from .models import Task


class CustomLoginView(LoginView):
    template_name = 'base/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('tasks')


class RegisterPage(FormView):
    template_name = 'base/register.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('tasks')

    @transaction.atomic
    def form_valid(self, form):
        try:
            user = form.save()
            if user is not None:
                login(self.request, user)
            return super().form_valid(form)
        except Exception as e:
            messages.error(self.request, f"Registration failed: {str(e)}")
            raise

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('tasks')
        return super().get(*args, **kwargs)


class TaskList(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = 'tasks'
    template_name = 'base/task_list.html'
    paginate_by = 10  # Добавляем пагинацию

    def get_queryset(self):
        # Получаем базовый queryset
        queryset = super().get_queryset()
        
        # Фильтруем задачи: либо личные, либо из проектов где пользователь участник
        queryset = queryset.filter(
            Q(user=self.request.user) | 
            Q(project__projectmember__user=self.request.user)
        ).distinct()
        
        # Фильтр по статусу выполнения
        complete_filter = self.request.GET.get('complete')
        if complete_filter in ['0', '1']:
            queryset = queryset.filter(complete=bool(int(complete_filter)))
        
        # Фильтр по проекту
        project_filter = self.request.GET.get('project')
        if project_filter:
            try:
                project = Project.objects.get(id=project_filter)
                if ProjectMember.objects.filter(project=project, user=self.request.user).exists():
                    queryset = queryset.filter(project=project)
            except Project.DoesNotExist:
                pass
        
        # Поиск по названию
        search_input = self.request.GET.get('search-area') or ''
        if search_input:
            queryset = queryset.filter(title__icontains=search_input)
        
        # Сортировка
        sort_by = self.request.GET.get('sort', '-created')
        if sort_by in ['title', '-title', 'deadline', '-deadline', 'created', '-created']:
            queryset = queryset.order_by(sort_by)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Добавляем информацию для фильтров
        context['search_input'] = self.request.GET.get('search-area') or ''
        context['complete_filter'] = self.request.GET.get('complete')
        context['project_filter'] = self.request.GET.get('project')
        context['sort_by'] = self.request.GET.get('sort', '-created')
        
        # Статистика задач
        context['total_count'] = self.get_queryset().count()
        context['incomplete_count'] = self.get_queryset().filter(complete=False).count()
        context['complete_count'] = self.get_queryset().filter(complete=True).count()
        
        # Список проектов для фильтра
        context['projects'] = Project.objects.filter(
            projectmember__user=self.request.user
        ).distinct()
        
        # Информация о структуре таблицы (если нужно оставить)
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'base_task'
                    ORDER BY ordinal_position
                """)
                context['table_structure'] = cursor.fetchall()
        
        return context


class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'base/task.html'

    def get_queryset(self):
        """Ограничиваем задачи только теми, которые пользователь может просматривать"""
        qs = super().get_queryset()
        return qs.filter(
            Q(user=self.request.user) | 
            Q(project__projectmember__user=self.request.user)
        ).distinct()


class TaskCreate(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm  # Используем форму TaskForm
    success_url = reverse_lazy('tasks')

    def form_valid(self, form):
        """Устанавливаем текущего пользователя как владельца задачи."""
        form.instance.user = self.request.user
        return super().form_valid(form)

    def get_initial(self):
        """Устанавливаем проект из GET-параметра, если он есть."""
        initial = super().get_initial()
        project_id = self.request.GET.get('project')
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                # Проверяем, что пользователь является участником проекта
                if ProjectMember.objects.filter(project=project, user=self.request.user).exists():
                    initial['project'] = project
            except Project.DoesNotExist:
                pass
        return initial

    @transaction.atomic
    def form_valid(self, form):
        try:
            form.instance.user = self.request.user
            
            # Проверяем, что если задача добавляется в проект, 
            # пользователь имеет на это права
            if form.cleaned_data.get('project'):
                project = form.cleaned_data['project']
                if not ProjectMember.objects.filter(project=project, user=self.request.user).exists():
                    messages.error(self.request, "You don't have permission to add tasks to this project")
                    return self.form_invalid(form)
            
            response = super().form_valid(form)
            messages.success(self.request, "Task created successfully!")
            return response
        except Exception as e:
            messages.error(self.request, f"Failed to create task: {str(e)}")
            raise

    def get_success_url(self):
        """Перенаправляем на страницу проекта, если задача была создана в проекте"""
        if self.object.project:
            return reverse_lazy('project-detail', kwargs={'pk': self.object.project.id})
        return super().get_success_url()


class TaskUpdate(LoginRequiredMixin, UpdateView):
    model = Task
    form_class = TaskForm  # Используем новую форму вместо fields
    success_url = reverse_lazy('tasks')

    def get_form_kwargs(self):
        """Добавляем текущего пользователя в kwargs формы для фильтрации проектов"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_queryset(self):
        """Ограничиваем задачи только теми, которые пользователь может редактировать"""
        qs = super().get_queryset()
        return qs.filter(
            Q(user=self.request.user) | 
            Q(project__projectmember__user=self.request.user, 
              project__projectmember__role__can_edit=True)
        ).distinct()  # Добавляем distinct для устранения дубликатов

    @transaction.atomic
    def form_valid(self, form):
        try:
            # Проверяем права на изменение проекта задачи
            if form.cleaned_data.get('project') and form.cleaned_data['project'] != self.object.project:
                new_project = form.cleaned_data['project']
                if not ProjectMember.objects.filter(project=new_project, user=self.request.user).exists():
                    messages.error(self.request, "You don't have permission to move task to this project")
                    return self.form_invalid(form)
            
            response = super().form_valid(form)
            messages.success(self.request, "Task updated successfully!")
            return response
        except Exception as e:
            messages.error(self.request, f"Failed to update task: {str(e)}")
            raise

    def get_success_url(self):
        """Перенаправляем на страницу проекта, если задача принадлежит проекту"""
        if self.object.project:
            return reverse_lazy('project-detail', kwargs={'pk': self.object.project.id})
        return super().get_success_url()


class DeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    success_url = reverse_lazy('tasks')

    @transaction.atomic
    def delete(self, request, *args, **kwargs):
        try:
            response = super().delete(request, *args, **kwargs)
            messages.success(request, "Task deleted successfully!")
            return response
        except Exception as e:
            messages.error(request, f"Failed to delete task: {str(e)}")
            raise

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class TaskReorder(View):
    @transaction.atomic
    def post(self, request):
        form = PositionForm(request.POST)

        if form.is_valid():
            positionList = form.cleaned_data["position"].split(',')
            
            try:
                with connection.cursor() as cursor:
                    for idx, task_id in enumerate(positionList, start=1):
                        cursor.execute(
                            "UPDATE base_task SET _order = %s WHERE id = %s AND user_id = %s",
                            [idx, task_id, request.user.id]
                        )
                messages.success(request, "Tasks reordered successfully!")
            except Exception as e:
                messages.error(request, f"Failed to reorder tasks: {str(e)}")
                raise
        return redirect(reverse_lazy('tasks'))


def get_task_count(request):
    if not request.user.is_authenticated:
        return HttpResponse("Unauthorized", status=401)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM base_task WHERE user_id = %s",
                [request.user.id]
            )
            count = cursor.fetchone()[0]
    return HttpResponse(f"Total tasks: {count}")


def get_table_info(request):
    if not request.user.is_authenticated:
        return HttpResponse("Please log in to view table info", status=401)

    with transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'base_task'
            """)
            columns = cursor.fetchall()

    result = "<h2>Database Table Structure: base_task</h2><ul>"
    for name, dtype in columns:
        result += f"<li><b>{name}</b>: {dtype}</li>"
    result += "</ul>"

    return HttpResponse(result)

class ProjectList(LoginRequiredMixin, ListView):
    model = Project
    context_object_name = 'projects'
    template_name = 'base/project_list.html'

    def get_queryset(self):
        return Project.objects.filter(
            projectmember__user=self.request.user
        ).distinct()

class ProjectCreate(LoginRequiredMixin, CreateView):
    model = Project
    form_class = ProjectForm
    template_name = 'base/project_form.html'  # Явно указываем шаблон
    success_url = reverse_lazy('projects')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        # Создаем запись участника с ролью владельца
        owner_role = Role.objects.get_or_create(name='Owner', can_create=True, can_edit=True, 
                                              can_delete=True, can_invite=True, can_manage_roles=True)[0]
        ProjectMember.objects.create(
            user=self.request.user,
            project=form.instance,
            role=owner_role
        )
        return response

class ProjectDetail(LoginRequiredMixin, ProjectMemberRequiredMixin, DetailView):
    model = Project
    context_object_name = 'project'
    template_name = 'base/project_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        context['members'] = ProjectMember.objects.filter(project=project)
        context['tasks'] = Task.objects.filter(project=project)
        context['is_owner'] = ProjectMember.objects.filter(
            project=project,
            user=self.request.user,
            role__name='Owner'
        ).exists()
        return context

class ProjectInvite(LoginRequiredMixin, ProjectOwnerRequiredMixin, View):
    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        form = InviteForm(request.POST)
        
        if form.is_valid():
            try:
                user = User.objects.get(email=form.cleaned_data['email'])
                if not ProjectMember.objects.filter(project=project, user=user).exists():
                    ProjectMember.objects.create(
                        project=project,
                        user=user,
                        role=form.cleaned_data['role']
                    )
                    messages.success(request, f"{user.username} добавлен в проект")
                else:
                    messages.error(request, "Пользователь уже в проекте")
            except User.DoesNotExist:
                messages.error(request, "Пользователь с таким email не найден")
        
        return redirect('project-detail', pk=pk)
class ProjectRemoveMember(LoginRequiredMixin, ProjectOwnerRequiredMixin, View):
    def post(self, request, project_id, member_id):
        member = get_object_or_404(ProjectMember, id=member_id, project_id=project_id)
        if member.role.name != 'Owner':  # Нельзя удалить владельца
            member.delete()
            messages.success(request, "Участник удален из проекта")
        return redirect('project-detail', pk=project_id)