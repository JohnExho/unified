from django.contrib import admin
from .models import CustomUser, Systems, SystemMembership, Logs, Address
from django.contrib.auth.admin import UserAdmin


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'is_email_verified', 'is_staff', 'is_active')
    
    def get_fieldsets(self, request, obj=None):
        # Remove first_name and last_name from the default fieldsets since they're encrypted
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets = list(fieldsets)
        # Modify the personal info fieldset to use encrypted field names
        for i, (section_name, section_dict) in enumerate(fieldsets):
            if section_name == 'Personal info':
                fields = list(section_dict['fields'])
                # Remove old field names if present
                fields = [f for f in fields if f not in ('first_name', 'last_name')]
                # Add encrypted field names
                fields.extend(['_first_name', '_last_name', '_middle_name'])
                fieldsets[i] = (section_name, {**section_dict, 'fields': tuple(fields)})
        
        # Add custom fields
        fieldsets.append(('Additional Info', {'fields': ('avatar', 'bio', '_phone_number', 'is_email_verified')}))
        return fieldsets
    
    def get_add_fieldsets(self, request):
        # Customize add form fieldsets
        add_fieldsets = super().get_fieldsets(request, None)
        add_fieldsets = list(add_fieldsets)
        
        # Modify the personal info fieldset for add form
        for i, (section_name, section_dict) in enumerate(add_fieldsets):
            if section_name == 'Personal info':
                fields = list(section_dict['fields'])
                fields = [f for f in fields if f not in ('first_name', 'last_name')]
                fields.extend(['_first_name', '_last_name', '_middle_name'])
                add_fieldsets[i] = (section_name, {**section_dict, 'fields': tuple(fields)})
        
        # Add custom fields
        add_fieldsets.append(('Additional Info', {'fields': ('email', 'avatar', 'bio', '_phone_number', 'is_email_verified')}))
        return add_fieldsets

@admin.register(Systems)
class SystemsAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'terms_of_service', 'created_at', 'updated_at')
    search_fields = ('name', 'description')

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
