from django.db import migrations


def update_system_descriptions(apps, schema_editor):
    Systems = apps.get_model("core", "Systems")

    Systems.objects.filter(name="communityextensionservices").update(
        description="Faculty Contribution Module."
    )
    Systems.objects.filter(name="informationmanagement").update(
        description="Manage inventory records, stock levels, and asset movement."
    )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_add_scholarshipmanagement_system"),
    ]

    operations = [
        migrations.RunPython(
            update_system_descriptions,
            reverse_code=migrations.RunPython.noop,
        ),
    ]