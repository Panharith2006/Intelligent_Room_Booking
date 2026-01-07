from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ("booking", "0006_alter_room_room_number"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            ALTER TABLE rooms DROP INDEX room_number;
            """,
            reverse_sql="""
            CREATE UNIQUE INDEX room_number ON rooms (room_number);
            """
        ),
    ]
