from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0013_fix_room_schema'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='room',
            name='building_name',
        ),
        migrations.RemoveField(
            model_name='room',
            name='building_type',
        ),
    ]
