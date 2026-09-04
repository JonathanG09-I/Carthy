import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bienestar', '0007_resource'),
    ]

    operations = [
        migrations.RenameField(
            model_name='resource',
            old_name='title',
            new_name='title_en',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='short_description',
            new_name='short_description_en',
        ),
        migrations.RenameField(
            model_name='resource',
            old_name='full_content',
            new_name='full_content_en',
        ),
        migrations.AddField(
            model_name='resource',
            name='title_es',
            field=models.CharField(blank=True, max_length=200, verbose_name='Spanish Title'),
        ),
        migrations.AddField(
            model_name='resource',
            name='short_description_es',
            field=models.TextField(blank=True, verbose_name='Spanish Description'),
        ),
        migrations.AddField(
            model_name='resource',
            name='full_content_es',
            field=models.TextField(blank=True, verbose_name='Spanish Content'),
        ),
        migrations.AddField(
            model_name='resource',
            name='source_author',
            field=models.CharField(blank=True, help_text='Author credited by the source organization (optional).', max_length=120),
        ),
        migrations.AlterField(
            model_name='resource',
            name='title_en',
            field=models.CharField(max_length=200, verbose_name='English Title'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='short_description_en',
            field=models.TextField(help_text='Brief summary shown on cards (EN).', verbose_name='English Description'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='full_content_en',
            field=models.TextField(blank=True, help_text='Full article body (EN). Use ## for section headings.', verbose_name='English Content'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='additional_sources',
            field=models.TextField(blank=True, help_text='Extra sources, one per line: Name|https://example.com|Author|YYYY-MM-DD'),
        ),
        migrations.AlterField(
            model_name='resource',
            name='keywords',
            field=models.CharField(blank=True, help_text='Comma-separated keywords for search (EN/ES mixed is fine).', max_length=300),
        ),
        migrations.CreateModel(
            name='DailyInspiration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text_en', models.TextField(verbose_name='Quote (English)')),
                ('text_es', models.TextField(blank=True, verbose_name='Quote (Spanish)')),
                ('author', models.CharField(blank=True, default='Carthy Support', max_length=120)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Daily Inspiration',
                'verbose_name_plural': 'Daily Inspirations',
                'ordering': ['-created_at'],
            },
        ),
    ]
