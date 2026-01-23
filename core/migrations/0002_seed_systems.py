from django.db import migrations

DEFAULT_TOS = """
By using this system, you agree to comply with all applicable laws and institutional policies.
Access is provided on an as-is basis. Misuse, unauthorized access, or abuse of system
resources may result in suspension or termination of access.

The administrators reserve the right to modify or discontinue services at any time.
Continued use of the system constitutes acceptance of any updated terms.
""".strip()


default_systems = [
    ('core', 'Core'),
    ('projectmanagement', 'Project Management'),
    ('librarymanagement', 'Library Management'),
    ('inventorymanagement', 'Inventory Management'),
    ('communityextensionservices', 'Community Extension Services'),
    ('informationmanagement', 'Information Management'),
    ('performanceevaluation', 'Performance Evaluation'),
]

def create_default_systems(apps, schema_editor):
    Systems = apps.get_model('core', 'Systems')
    for key, label in default_systems:
        Systems.objects.get_or_create(
            name=key,
            defaults={
                'description': f'{label} system',
                'terms_of_service': DEFAULT_TOS,
            }
        )

def create_super_user(apps, schema_editor):
    CustomUser = apps.get_model('core', 'CustomUser')
    if not CustomUser.objects.filter(username='admin').exists():
        user = CustomUser.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='password',
        )
        user.is_superuser = True
        user.is_staff = True  # Admin access to Django admin
        user.is_active = True
        user.save()

def create_super_user_membership(apps, schema_editor):
    CustomUser = apps.get_model('core', 'CustomUser')
    SystemMembership = apps.get_model('core', 'SystemMembership')
    try:
        user = CustomUser.objects.get(username='admin')
        for key, _ in default_systems:
            SystemMembership.objects.get_or_create(
                user=user,
                system_name=key,
                defaults={'system_role': 'superadmin'}
            )
    except CustomUser.DoesNotExist:
        pass

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_systems),
        migrations.RunPython(create_super_user),
        migrations.RunPython(create_super_user_membership),
    ]
