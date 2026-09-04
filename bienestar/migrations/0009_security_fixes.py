import hashlib

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import bienestar.models


def dedupe_emails(apps, schema_editor):
    Usuario = apps.get_model('bienestar', 'Usuario')
    seen = {}
    for user in Usuario.objects.exclude(email='').exclude(email__isnull=True).order_by('id'):
        key = (user.email or '').strip().lower()
        if not key:
            user.email = None
            user.save(update_fields=['email'])
            continue
        if key in seen:
            # Keep first account; rename later duplicates so unique can apply
            user.email = f'dupe.{user.id}.{key}'[:254]
            user.save(update_fields=['email'])
        else:
            seen[key] = user.id
            if user.email != key:
                user.email = key
                user.save(update_fields=['email'])

    for user in Usuario.objects.filter(email=''):
        user.email = None
        user.save(update_fields=['email'])


class Migration(migrations.Migration):

    dependencies = [
        ('bienestar', '0008_bilingual_resources_and_inspiration'),
    ]

    operations = [
        migrations.RunPython(dedupe_emails, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='usuario',
            name='email',
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name='registroanimo',
            name='fecha',
            field=models.DateField(default=bienestar.models.local_today),
        ),
        migrations.CreateModel(
            name='PasswordResetToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code_hash', models.CharField(max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('used_at', models.DateTimeField(blank=True, null=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='password_reset_tokens', to='bienestar.usuario')),
            ],
            options={
                'verbose_name': 'Password Reset Token',
                'verbose_name_plural': 'Password Reset Tokens',
                'ordering': ['-created_at'],
            },
        ),
    ]
