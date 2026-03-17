from django.contrib import admin
from .models import Team, Project, Task, CalendarEvent, Notification, Report

# ----------------------
# Team Admin
# ----------------------
@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'member_count')
    search_fields = ('name',)
    filter_horizontal = ('members',)

    def member_count(self, obj):
        return obj.members.count()
    member_count.short_description = 'Members'

# ----------------------
# Project Admin
# ----------------------
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'research_method', 'publication_scope', 'source_type', 'team', 'start_date', 'end_date', 'created_by', 'status')
    list_filter = ('research_method', 'publication_scope', 'source_type', 'team', 'start_date', 'end_date')
    search_fields = ('name', 'description', 'created_by__username')

# ----------------------
# Task Admin
# ----------------------
@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'get_assignees', 'status', 'priority', 'due_date')
    list_filter = ('status', 'priority', 'due_date', 'project')
    search_fields = ('title', 'description', 'assigned_to__username')
    filter_horizontal = ('assigned_to',)
    
    def get_assignees(self, obj):
        return ", ".join([user.username for user in obj.assigned_to.all()[:3]]) or "Unassigned"
    get_assignees.short_description = 'Assigned To'

# ----------------------
# CalendarEvent Admin
# ----------------------
@admin.register(CalendarEvent)
class CalendarEventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'related_project', 'related_task')
    list_filter = ('start_time', 'end_time')
    search_fields = ('title', 'description')

# ----------------------
# Notification Admin
# ----------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'message', 'read', 'created_at', 'related_project', 'related_task')
    list_filter = ('read', 'created_at')
    search_fields = ('recipient__username', 'message')

# ----------------------
# Report Admin
# ----------------------
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'generated_by', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('project__name', 'generated_by__username')
