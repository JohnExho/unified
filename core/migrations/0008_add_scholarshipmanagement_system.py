from django.db import migrations


def add_scholarship_system(apps, schema_editor):
    Systems = apps.get_model('core', 'Systems')
    SystemMembership = apps.get_model('core', 'SystemMembership')
    CustomUser = apps.get_model('core', 'CustomUser')

    system, _ = Systems.objects.get_or_create(
        name='scholarshipmanagement',
        defaults={
            'description': 'Manage and administer scholarship programs and applications.',
            'terms_of_service': 'Terms of Service for Scholarship Management. Please review and accept to use this system.',
        }
    )

    try:
        admin_user = CustomUser.objects.get(username='admin')
        SystemMembership.objects.get_or_create(
            user=admin_user,
            system_name='scholarshipmanagement',
            defaults={'system_role': 'superadmin'},
        )
    except CustomUser.DoesNotExist:
        pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_alter_systemmembership_system_role'),
    ]

    operations = [
        migrations.RunPython(add_scholarship_system, reverse_code=migrations.RunPython.noop),
    ]
