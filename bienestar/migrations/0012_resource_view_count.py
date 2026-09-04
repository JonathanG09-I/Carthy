from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bienestar', '0011_dailyinspiration_audience'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='view_count',
            field=models.PositiveIntegerField(default=0, help_text='Times this resource detail was opened.'),
        ),
    ]
