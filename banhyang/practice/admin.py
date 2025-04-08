from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

# Register your models here.
from .models import User
from .forms import AdminUserChangeForm, AdminUserCreationForm

class UserAdmin(BaseUserAdmin):
    form = AdminUserChangeForm
    add_form = AdminUserCreationForm

    list_display = ('username', 'email', 'is_staff')
    list_filter = ('is_staff',)
    fieldsets = (
        (None, {'fields': ('username', 'password','name', 'email', 'student_id', 'phone_number', 'is_confirmed', 'is_active')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2','name', 'email', 'student_id', 'phone_number', 'is_confirmed', 'is_active')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser',)}),
    )
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ()

admin.site.register(User, UserAdmin)