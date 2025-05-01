from django.urls import path
from .views import TaskList, TaskDetail, TaskCreate, TaskUpdate, DeleteView, CustomLoginView, RegisterPage, TaskReorder
from django.contrib.auth.views import LogoutView
from .views import get_task_count
from .views import get_table_info
from .views import ProjectList, ProjectCreate, ProjectDetail, ProjectInvite
from .views import ProjectRemoveMember

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('register/', RegisterPage.as_view(), name='register'),

    path('', TaskList.as_view(), name='tasks'),
    path('task/<int:pk>/', TaskDetail.as_view(), name='task'),
    path('task-create/', TaskCreate.as_view(), name='task-create'),
    path('task-update/<int:pk>/', TaskUpdate.as_view(), name='task-update'),
    path('task-delete/<int:pk>/', DeleteView.as_view(), name='task-delete'),
    path('task-reorder/', TaskReorder.as_view(), name='task-reorder'),
    path('task-count/', get_task_count, name='task-count'),
    path('table-info/', get_table_info, name='table-info'),
     path('projects/', ProjectList.as_view(), name='projects'),
    path('project-create/', ProjectCreate.as_view(), name='project-create'),
    path('project/<int:pk>/', ProjectDetail.as_view(), name='project-detail'),
    path('project/<int:pk>/invite/', ProjectInvite.as_view(), name='project-invite'),
    path('project/<int:project_id>/remove-member/<int:member_id>/', ProjectRemoveMember.as_view(), name='project-remove-member'),

]
