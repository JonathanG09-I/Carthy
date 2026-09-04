from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Sesion, NotaSegura, Resource, DailyInspiration, ContactMessage, SolicitudProfesional


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Carthy', {
            'fields': ('rol', 'foto_url', 'fecha_registro'),
        }),
    )
    list_display = ('username', 'email', 'first_name', 'last_name', 'rol', 'is_staff')
    list_filter = ('rol', 'is_staff', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')


@admin.register(Sesion)
class SesionAdmin(admin.ModelAdmin):
    list_display = ('id', 'estudiante', 'escuchador', 'fecha_hora', 'estado', 'modalidad')
    list_filter = ('estado', 'modalidad', 'fecha_hora')
    search_fields = ('estudiante__first_name', 'estudiante__last_name', 'escuchador__first_name')
    date_hierarchy = 'fecha_hora'
    readonly_fields = ('creado_en',)


@admin.register(NotaSegura)
class NotaSeguraAdmin(admin.ModelAdmin):
    list_display = ('id', 'sesion', 'autor', 'ultima_modificacion')
    list_filter = ('autor', 'ultima_modificacion')
    readonly_fields = ('ultima_modificacion',)


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = (
        'title_en',
        'title_es',
        'resource_type',
        'category',
        'author',
        'reading_time',
        'is_featured',
        'is_published',
        'publication_date',
    )
    list_filter = ('resource_type', 'category', 'is_featured', 'is_published', 'publication_date')
    search_fields = (
        'title_en', 'title_es',
        'short_description_en', 'short_description_es',
        'keywords', 'author', 'source_name',
    )
    list_editable = ('is_featured', 'is_published')
    date_hierarchy = 'publication_date'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('English Content', {
            'fields': ('title_en', 'short_description_en', 'full_content_en'),
        }),
        ('Spanish Content', {
            'fields': ('title_es', 'short_description_es', 'full_content_es'),
            'description': 'Same resource record — Spanish version used when the UI language is ES.',
        }),
        ('Classification', {
            'fields': ('category', 'resource_type', 'cover_image', 'keywords'),
        }),
        ('Attribution & Sources', {
            'fields': (
                'author',
                'source_name',
                'source_url',
                'source_author',
                'additional_sources',
                'reading_time',
                'publication_date',
            ),
        }),
        ('Video (optional)', {
            'classes': ('collapse',),
            'fields': ('youtube_url', 'video_duration', 'video_channel'),
        }),
        ('Download (optional)', {
            'classes': ('collapse',),
            'fields': ('pdf_file',),
        }),
        ('Publishing', {
            'fields': ('is_featured', 'is_published', 'created_at', 'updated_at'),
        }),
    )


@admin.register(DailyInspiration)
class DailyInspirationAdmin(admin.ModelAdmin):
    list_display = ('text_en', 'author', 'audience', 'is_active', 'created_at')
    list_filter = ('is_active', 'audience')
    search_fields = ('text_en', 'text_es', 'author')
    list_editable = ('is_active', 'audience')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'created_at', 'is_read', 'is_replied')
    list_filter = ('is_read', 'is_replied', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    list_editable = ('is_read', 'is_replied')
    date_hierarchy = 'created_at'
    readonly_fields = ('name', 'email', 'subject', 'message', 'created_at')
    ordering = ('-created_at',)

    fieldsets = (
        ('Message', {
            'fields': ('name', 'email', 'subject', 'message', 'created_at'),
        }),
        ('Status', {
            'fields': ('is_read', 'is_replied'),
        }),
    )


@admin.register(SolicitudProfesional)
class SolicitudProfesionalAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'email', 'profesion', 'especialidad', 'institucion', 'estado', 'fecha_solicitud', 'fecha_revision', 'revisado_por')
    list_filter = ('estado', 'profesion', 'fecha_solicitud')
    search_fields = ('nombre_completo', 'email', 'profesion', 'institucion')
    ordering = ('-fecha_solicitud',)
    readonly_fields = ('estado', 'fecha_solicitud', 'fecha_revision', 'revisado_por')
    fields = (
        'nombre_completo', 'email', 'telefono', 'profesion', 'especialidad', 'institucion',
        'informacion_adicional', 'observacion_revision', 'estado', 'fecha_solicitud',
        'fecha_revision', 'revisado_por',
    )
    actions = ('aprobar_solicitudes', 'rechazar_solicitudes')

    @admin.action(description='Approve selected professional requests')
    def aprobar_solicitudes(self, request, queryset):
        aprobadas = 0
        for solicitud in queryset.select_related('revisado_por'):
            try:
                solicitud.aprobar(request.user)
                aprobadas += 1
            except ValidationError as error:
                self.message_user(request, f'{solicitud.email}: {error}', level='ERROR')
        if aprobadas:
            self.message_user(request, f'{aprobadas} professional request(s) approved successfully.')

    @admin.action(description='Reject selected professional requests')
    def rechazar_solicitudes(self, request, queryset):
        rechazadas = 0
        for solicitud in queryset.select_related('revisado_por'):
            try:
                solicitud.rechazar(request.user)
                rechazadas += 1
            except ValidationError as error:
                self.message_user(request, f'{solicitud.email}: {error}', level='ERROR')
        if rechazadas:
            self.message_user(request, f'{rechazadas} professional request(s) rejected successfully.')
