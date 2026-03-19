from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_user_cancellation_policy_counters'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='position',
            field=models.CharField(
                blank=True,
                help_text='Academic position (e.g., Lecturer, Assistant Professor).',
                max_length=100,
                verbose_name='Position',
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='booking_approval_status',
            field=models.CharField(
                choices=[('pending', 'Pending Review'), ('approved', 'Approved'), ('rejected', 'Rejected')],
                default='pending',
                help_text='Controls whether lecturer can make room bookings.',
                max_length=20,
                verbose_name='Booking Approval Status',
            ),
        ),
        migrations.AlterField(
            model_name='user',
            name='student_id',
            field=models.CharField(
                blank=True,
                help_text='6-20 character lecturer identification.',
                max_length=20,
                null=True,
                unique=True,
                verbose_name='Lecturer ID',
            ),
        ),
    ]
