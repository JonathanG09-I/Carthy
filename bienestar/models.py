from django.db import models, transaction
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
import re


def local_today():
    return timezone.localdate()


# 1. MODELO DE USUARIO PERSONALIZADO (Estudiantes y Escuchadores)
class Usuario(AbstractUser):
    ROLES_CHOICES = (
        ('estudiante', 'Estudiante'),
        ('escuchador', 'Escuchador / Profesional'),
        ('admin', 'Administrador'),
    )

    rol = models.CharField(max_length=20, choices=ROLES_CHOICES, default='estudiante')
    # Modificado a TextField para poder almacenar cadenas Base64 completas de las imágenes de perfil
    foto_url = models.TextField(blank=True, null=True, help_text="Contenido Base64 o URL de la foto de perfil")
    fecha_registro = models.DateTimeField(default=timezone.now)
    # Override AbstractUser.email to enforce uniqueness across accounts
    email = models.EmailField(blank=True, unique=True, null=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_rol_display()})"

    def save(self, *args, **kwargs):
        # Normalize empty emails to NULL so unique constraint allows multiple blank accounts
        if self.email == '':
            self.email = None
        super().save(*args, **kwargs)


# 2. MODELO DE SESIONES (Citas de Escucha)
class Sesion(models.Model):
    ESTADOS_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('confirmada', 'Confirmada'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
        ('reagendada', 'Rescheduled - Pending Your Approval'),
    )

    MODALIDAD_CHOICES = (
        ('virtual', 'Virtual (Teams/Zoom)'),
        ('presencial', 'Presencial'),
    )

    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sesiones_como_estudiante')
    escuchador = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='sesiones_como_escuchador')

    fecha_hora = models.DateTimeField(help_text="Fecha y hora de la sesión")
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='pendiente')
    modalidad = models.CharField(max_length=20, choices=MODALIDAD_CHOICES, default='virtual')
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sesión de Escucha"
        verbose_name_plural = "Sesiones de Escucha"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"Sesión: {self.estudiante.first_name} con {self.escuchador.first_name} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"


# 3. MODELO DE NOTAS SEGURAS (Confidencial)
class NotaSegura(models.Model):
    sesion = models.OneToOneField(Sesion, on_delete=models.CASCADE, related_name='nota_segura')
    autor = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='notas_escritas')
    contenido_encriptado = models.TextField(help_text="Resumen privado de la sesión.")
    ultima_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Nota Privada"
        verbose_name_plural = "Notas Privadas"

    def __str__(self):
        return f"Nota confidencial - Sesión {self.sesion.id}"


# 4. MODELO DE DISPONIBILIDAD (Bloques de horario semanal por escuchador)
class Disponibilidad(models.Model):
    DIAS_SEMANA_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    escuchador = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='bloques_disponibilidad')
    dia_semana = models.IntegerField(choices=DIAS_SEMANA_CHOICES, help_text="0=Lunes ... 6=Domingo")
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        verbose_name = "Bloque de Disponibilidad"
        verbose_name_plural = "Bloques de Disponibilidad"
        ordering = ['dia_semana', 'hora_inicio']

    def __str__(self):
        return f"{self.escuchador.get_full_name()} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"


# 5. NUEVO MODELO DE MENSAJES (Para el Chat Real)
class Mensaje(models.Model):
    emisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_enviados')
    receptor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_recibidos')
    contenido = models.TextField(help_text="Contenido del mensaje en texto plano.")
    leido = models.BooleanField(default=False, help_text="Si el receptor ya abrió esta conversación después de recibirlo.")
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensaje de Chat"
        verbose_name_plural = "Mensajes de Chat"
        ordering = ['creado_en']

    def __str__(self):
        return f"Mensaje de {self.emisor.username} para {self.receptor.username} ({self.creado_en.strftime('%d/%m/%Y %H:%M')})"


# 6. MODELO DE REGISTRO DE ÁNIMO DIARIO (Mood Tracker)
class RegistroAnimo(models.Model):
    ANIMOS_CHOICES = (
        ('genial', 'Great'),
        ('bien', 'Good'),
        ('normal', 'Okay'),
        ('mal', 'Down'),
        ('enojado', 'Angry'),
    )

    estudiante = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='registros_animo')
    fecha = models.DateField(default=local_today)
    animo = models.CharField(max_length=20, choices=ANIMOS_CHOICES)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de Ánimo"
        verbose_name_plural = "Registros de Ánimo"
        # Garantiza a nivel de base de datos que solo puede existir UN registro
        # por estudiante por día, sin depender únicamente de validación en código.
        unique_together = ('estudiante', 'fecha')
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.estudiante.username} - {self.fecha} - {self.get_animo_display()}"


# 7. MODELO DE RECURSOS EDUCATIVOS (Wellness Hub / Resources)
class Resource(models.Model):
    CATEGORY_CHOICES = (
        ('mental_health', 'Mental Health'),
        ('stress_management', 'Stress Management'),
        ('academic_success', 'Academic Success'),
        ('healthy_habits', 'Healthy Habits'),
        ('sleep', 'Sleep'),
        ('relationships', 'Relationships'),
        ('mindfulness', 'Mindfulness'),
    )

    CATEGORY_LABELS_ES = {
        'mental_health': 'Salud Mental',
        'stress_management': 'Manejo del Estrés',
        'academic_success': 'Éxito Académico',
        'healthy_habits': 'Hábitos Saludables',
        'sleep': 'Sueño',
        'relationships': 'Relaciones',
        'mindfulness': 'Atención plena',
    }

    TYPE_CHOICES = (
        ('article', 'Article'),
        ('video', 'Video'),
        ('download', 'Download'),
    )

    TYPE_LABELS_ES = {
        'article': 'Artículo',
        'video': 'Video',
        'download': 'Descarga',
    }

    CATEGORY_COVER_DEFAULTS = {
        'mental_health': 'images/resource-covers/mental_health.svg',
        'stress_management': 'images/resource-covers/stress_management.svg',
        'academic_success': 'images/resource-covers/academic_success.svg',
        'healthy_habits': 'images/resource-covers/healthy_habits.svg',
        'sleep': 'images/resource-covers/sleep.svg',
        'relationships': 'images/resource-covers/relationships.svg',
        'mindfulness': 'images/resource-covers/mindfulness.svg',
    }

    # English content
    title_en = models.CharField(max_length=200, verbose_name='English Title')
    short_description_en = models.TextField(verbose_name='English Description', help_text='Brief summary shown on cards (EN).')
    full_content_en = models.TextField(blank=True, verbose_name='English Content', help_text='Full article body (EN). Use ## for section headings.')

    # Spanish content (same record — no duplicate articles)
    title_es = models.CharField(max_length=200, blank=True, verbose_name='Spanish Title')
    short_description_es = models.TextField(blank=True, verbose_name='Spanish Description')
    full_content_es = models.TextField(blank=True, verbose_name='Spanish Content')

    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES)
    resource_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='article')
    cover_image = models.ImageField(upload_to='resources/covers/', blank=True, null=True)
    author = models.CharField(max_length=120, blank=True)
    source_name = models.CharField(max_length=200, blank=True, help_text='e.g. World Health Organization')
    source_url = models.URLField(blank=True)
    source_author = models.CharField(max_length=120, blank=True, help_text='Author credited by the source organization (optional).')
    additional_sources = models.TextField(
        blank=True,
        help_text='Extra sources, one per line: Name|https://example.com|Author|YYYY-MM-DD',
    )
    reading_time = models.PositiveIntegerField(
        default=5,
        help_text='Estimated reading/watching time in minutes.',
    )
    keywords = models.CharField(
        max_length=300,
        blank=True,
        help_text='Comma-separated keywords for search (EN/ES mixed is fine).',
    )
    youtube_url = models.URLField(blank=True, help_text='YouTube link for video resources.')
    video_duration = models.CharField(max_length=20, blank=True, help_text='e.g. "8:24"')
    video_channel = models.CharField(max_length=120, blank=True)
    pdf_file = models.FileField(upload_to='resources/pdfs/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    view_count = models.PositiveIntegerField(default=0, help_text='Times this resource detail was opened.')
    publication_date = models.DateField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Resource'
        verbose_name_plural = 'Resources'
        ordering = ['-publication_date', '-created_at']

    def __str__(self):
        return f'{self.title_en} ({self.get_resource_type_display()})'

    def get_title(self, lang='en'):
        if lang == 'es' and (self.title_es or '').strip():
            return self.title_es
        return self.title_en

    def get_short_description(self, lang='en'):
        if lang == 'es' and (self.short_description_es or '').strip():
            return self.short_description_es
        return self.short_description_en

    def get_full_content(self, lang='en'):
        if lang == 'es' and (self.full_content_es or '').strip():
            return self.full_content_es
        return self.full_content_en

    def get_category_label(self, lang='en'):
        if lang == 'es':
            return self.CATEGORY_LABELS_ES.get(self.category, self.get_category_display())
        return self.get_category_display()

    def get_type_label(self, lang='en'):
        if lang == 'es':
            return self.TYPE_LABELS_ES.get(self.resource_type, self.get_resource_type_display())
        return self.get_resource_type_display()

    def get_cover_url(self):
        """Uploaded cover or category default illustration."""
        if self.cover_image:
            return self.cover_image.url
        from django.templatetags.static import static
        path = self.CATEGORY_COVER_DEFAULTS.get(self.category, 'images/resource-covers/mental_health.svg')
        return static(path)

    def get_youtube_embed_id(self):
        """Extract YouTube video id from common URL formats."""
        url = (self.youtube_url or '').strip()
        if not url:
            return ''
        if 'youtu.be/' in url:
            return url.split('youtu.be/')[-1].split('?')[0].split('/')[0]
        if 'watch?v=' in url:
            return url.split('watch?v=')[-1].split('&')[0]
        if '/embed/' in url:
            return url.split('/embed/')[-1].split('?')[0]
        return ''

    def get_sources_list(self):
        """Return list of {name, url, author, date} including primary and additional sources."""
        sources = []
        pub = self.publication_date.isoformat() if self.publication_date else ''
        if self.source_name or self.source_url:
            sources.append({
                'name': self.source_name or self.source_url,
                'url': self.source_url or '',
                'author': self.source_author or self.author or '',
                'date': pub,
            })
        for line in (self.additional_sources or '').splitlines():
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split('|')]
            sources.append({
                'name': parts[0] if parts else line,
                'url': parts[1] if len(parts) > 1 else '',
                'author': parts[2] if len(parts) > 2 else '',
                'date': parts[3] if len(parts) > 3 else '',
            })
        return sources

    def extract_toc(self, lang='en'):
        """
        Build a table of contents from markdown-like ## headings in full content.
        Returns list of {id, title}.
        """
        import re
        content = self.get_full_content(lang) or ''
        toc = []
        for i, match in enumerate(re.finditer(r'^##\s+(.+)$', content, re.MULTILINE)):
            title = match.group(1).strip()
            slug = re.sub(r'[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ]+', '-', title).strip('-').lower() or f'section-{i+1}'
            toc.append({'id': f'section-{slug}-{i}', 'title': title})
        return toc


# 8. CITAS DE INSPIRACIÓN DIARIA (Daily Inspiration)
class DailyInspiration(models.Model):
    AUDIENCE_CHOICES = (
        ('ambos', 'Both'),
        ('estudiante', 'Student'),
        ('escuchador', 'Psych.'),
    )

    text_en = models.TextField(verbose_name='Quote (English)')
    text_es = models.TextField(blank=True, verbose_name='Quote (Spanish)')
    author = models.CharField(max_length=120, blank=True, default='Carthy Support')
    audience = models.CharField(
        max_length=20,
        choices=AUDIENCE_CHOICES,
        default='ambos',
        help_text='Who should see this quote on the dashboard.',
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Daily Inspiration'
        verbose_name_plural = 'Daily Inspirations'
        ordering = ['-created_at']

    def __str__(self):
        preview = (self.text_en or '')[:60]
        return f'{preview}…' if len(self.text_en or '') > 60 else preview

    def get_text(self, lang='en'):
        if lang == 'es' and (self.text_es or '').strip():
            return self.text_es
        return self.text_en


# 9. TOKENS DE RESTABLECIMIENTO DE CONTRASEÑA (one-time codes)
class PasswordResetToken(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='password_reset_tokens')
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        ordering = ['-created_at']

    def __str__(self):
        return f'Reset for {self.usuario_id} @ {self.created_at}'

    @property
    def is_valid(self):
        return self.used_at is None and timezone.now() < self.expires_at


# 10. MENSAJES DE CONTACTO (Landing form — no email sending)
class ContactMessage(models.Model):
    name = models.CharField(max_length=120, verbose_name='Full Name')
    email = models.EmailField(verbose_name='Email')
    subject = models.CharField(max_length=200, verbose_name='Subject')
    message = models.TextField(verbose_name='Message')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Date')
    is_read = models.BooleanField(default=False, verbose_name='Read')
    is_replied = models.BooleanField(default=False, verbose_name='Replied')

    class Meta:
        verbose_name = 'Contact Message'
        verbose_name_plural = 'Contact Messages'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.subject} — {self.name} ({self.email})'


# 11. SOLICITUDES DE CUENTA PROFESIONAL
class SolicitudProfesional(models.Model):
    ESTADOS_CHOICES = (
        ('pendiente', 'Pendiente'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
    )

    nombre_completo = models.CharField(max_length=120)
    email = models.EmailField()
    telefono = models.CharField(max_length=30, blank=True)
    profesion = models.CharField(max_length=120)
    especialidad = models.CharField(max_length=120, blank=True)
    institucion = models.CharField(max_length=160, blank=True)
    informacion_adicional = models.TextField(blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='pendiente')
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_revision = models.DateTimeField(null=True, blank=True)
    revisado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='solicitudes_profesionales_revisadas',
    )
    observacion_revision = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Solicitud profesional'
        verbose_name_plural = 'Solicitudes profesionales'
        ordering = ['-fecha_solicitud']

    def __str__(self):
        return f'{self.nombre_completo} — {self.get_estado_display()}'

    def clean(self):
        super().clean()
        if not (self.nombre_completo or '').strip():
            raise ValidationError({'nombre_completo': 'Full name is required.'})
        if not (self.profesion or '').strip():
            raise ValidationError({'profesion': 'Profession is required.'})

    @staticmethod
    def _username_profesional_disponible(email):
        """Create a unique internal username without exposing a password."""
        local = (email or '').split('@', 1)[0].lower()
        base = re.sub(r'[^a-z0-9._+-]+', '-', local).strip('-') or 'professional'
        base = f'professional-{base}'[:140]
        username = base
        suffix = 2
        while Usuario.objects.filter(username=username).exists():
            suffix_text = f'-{suffix}'
            username = f'{base[:150 - len(suffix_text)]}{suffix_text}'
            suffix += 1
        return username

    def aprobar(self, administrador):
        """Approve exactly one pending request and grant the existing listener role."""
        if self.estado != 'pendiente':
            raise ValidationError('Only pending requests can be approved.')

        with transaction.atomic():
            usuario = Usuario.objects.filter(email__iexact=self.email).first()
            if usuario is None:
                partes = self.nombre_completo.strip().split(' ', 1)
                usuario = Usuario.objects.create_user(
                    username=self._username_profesional_disponible(self.email),
                    email=self.email,
                    password=None,
                    first_name=partes[0],
                    last_name=partes[1] if len(partes) > 1 else '',
                    rol='escuchador',
                )
            elif usuario.rol == 'estudiante':
                usuario.rol = 'escuchador'
                usuario.save(update_fields=['rol'])
            elif usuario.rol != 'escuchador':
                raise ValidationError('This email belongs to an administrative account and cannot be promoted automatically.')

            self.estado = 'aprobada'
            self.fecha_revision = timezone.now()
            self.revisado_por = administrador
            self.save(update_fields=['estado', 'fecha_revision', 'revisado_por'])
        return usuario

    def rechazar(self, administrador):
        """Reject exactly one pending request without changing any user account."""
        if self.estado != 'pendiente':
            raise ValidationError('Only pending requests can be rejected.')
        self.estado = 'rechazada'
        self.fecha_revision = timezone.now()
        self.revisado_por = administrador
        self.save(update_fields=['estado', 'fecha_revision', 'revisado_por'])
