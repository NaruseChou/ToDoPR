from django.contrib import admin
from .models import Task, Project, ProjectMember, Role

class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    extra = 1

class ProjectAdmin(admin.ModelAdmin):
    inlines = [ProjectMemberInline]
    list_display = ('name', 'created_by', 'deadline')
    search_fields = ('name', 'description')

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'project', 'complete', 'deadline')
    list_filter = ('complete', 'project')
    search_fields = ('title', 'description')

admin.site.register(Task, TaskAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Role)