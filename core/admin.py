from django.contrib import admin
from .models import CustomUser,  SystemMembership, Logs, Address
from django.contrib.auth.admin import UserAdmin


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_email_verified', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('middle_name', 'avatar', 'bio', '_phone_number', 'is_email_verified',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('middle_name', 'avatar', 'bio', '_phone_number', 'is_email_verified')}),
    )

@admin.register(SystemMembership)
class SystemMembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'system_name', 'joined_at', 'system_role')
    list_filter = ('system_name', 'user', 'joined_at', 'system_role')
    search_fields = ('user__username', 'system_name', 'system_role')

@admin.register(Logs)
class LogsAdmin(admin.ModelAdmin):
    # Use actual fields from your model
    list_display = ('user', 'system_name', 'target_model', 'action', 'created_at')
    list_filter = ('system_name', 'target_model', 'action', 'user')
    search_fields = ('user__username', 'description')

@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('user', 'type', 'full_address', 'city', 'province', 'postal_code', 'country')
    list_filter = ('type', 'user')
    search_fields = ('full_address', 'city', 'province')
