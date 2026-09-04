from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bienestar', '0012_resource_view_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitudProfesional',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_completo', models.CharField(max_length=120)),
                ('email', models.EmailField(max_length=254)),
                ('telefono', models.CharField(blank=True, max_length=30)),
                ('profesion', models.CharField(max_length=120)),
                ('especialidad', models.CharField(blank=True, max_length=120)),
                ('institucion', models.CharField(blank=True, max_length=160)),
                ('informacion_adicional', models.TextField(blank=True)),
                ('estado', models.CharField(choices=[('pendiente', 'Pendiente'), ('aprobada', 'Aprobada'), ('rechazada', 'Rechazada')], default='pendiente', max_length=20)),
                ('fecha_solicitud', models.DateTimeField(auto_now_add=True)),
                ('fecha_revision', models.DateTimeField(blank=True, null=True)),
                ('observacion_revision', models.TextField(blank=True)),
                ('revisado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes_profesionales_revisadas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Solicitud profesional',
                'verbose_name_plural': 'Solicitudes profesionales',
                'ordering': ['-fecha_solicitud'],
            },
        ),
    ]
