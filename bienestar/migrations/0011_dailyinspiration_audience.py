from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bienestar', '0010_contactmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='dailyinspiration',
            name='audience',
            field=models.CharField(
                choices=[
                    ('ambos', 'Both'),
                    ('estudiante', 'Student'),
                    ('escuchador', 'Psych.'),
                ],
                default='ambos',
                help_text='Who should see this quote on the dashboard.',
                max_length=20,
            ),
        ),
    ]
