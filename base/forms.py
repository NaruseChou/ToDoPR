from django import forms
from .models import Project, Task, Role
# Reordering Form and View

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ['name', 'description', 'deadline']
        widgets = {
            'deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'complete', 'deadline', 'project']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Извлекаем user из kwargs
        super().__init__(*args, **kwargs)
        if user:
            # Фильтруем проекты только для тех, где пользователь является участником
            self.fields['project'].queryset = Project.objects.filter(
                projectmember__user=user
            ).distinct()

class InviteForm(forms.Form):
    email = forms.EmailField()
    role = forms.ModelChoiceField(queryset=Role.objects.all())

class PositionForm(forms.Form):
    position = forms.CharField()