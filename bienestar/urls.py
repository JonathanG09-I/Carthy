from django.urls import path
from .views import (
    home,
    app,
    lista_sesiones_api,
    login_api,
    registro_api,
    crear_solicitud_profesional_api,
    sesion_actual_api,
    obtener_psicologos_api,
    crear_sesion_api,
    demo_movil,
    guardar_nota_api,
    obtener_nota_api,
    cambiar_estado_sesion_api,
    reagendar_sesion_api,
    actualizar_perfil_api,
    cambiar_password_api,
    dashboard_resumen_api,
    listar_disponibilidad_api,
    agregar_disponibilidad_api,
    eliminar_disponibilidad_api,
    obtener_contactos_chat_api,
    listar_mensajes_api,
    enviar_mensaje_api,
    animo_hoy_api,
    registrar_animo_api,
    notificaciones_api,
    notificaciones_marcar_api,
    recuperar_password_api,
    logout_api,
)
from .resource_views import (
    lista_recursos_api,
    detalle_recurso_api,
    recurso_detalle,
    recursos_publicos,
    inspiracion_diaria_api,
)
from .contact_views import contact_message_api

urlpatterns = [
    path('', home, name='home'),
    path('app/', app, name='app'),

    path('api/login/', login_api, name='login_api'),
    path('api/registro/', registro_api, name='registro_api'),
    path('api/solicitudes-profesionales/', crear_solicitud_profesional_api, name='crear_solicitud_profesional_api'),
    path('api/logout/', logout_api, name='logout_api'),
    path('api/recuperar-password/', recuperar_password_api, name='recuperar_password_api'),
    path('api/contact/', contact_message_api, name='contact_message_api'),
    path('api/sesion-actual/', sesion_actual_api, name='sesion_actual_api'),
    path('api/actualizar-perfil/', actualizar_perfil_api, name='actualizar_perfil_api'),
    path('api/cambiar-password/', cambiar_password_api, name='cambiar_password_api'),
    path('api/dashboard-resumen/', dashboard_resumen_api, name='dashboard_resumen_api'),

    path('api/sesiones/', lista_sesiones_api, name='lista_sesiones_api'),
    path('api/psicologos/', obtener_psicologos_api, name='obtener_psicologos_api'),
    path('api/crear-sesion/', crear_sesion_api, name='crear_sesion_api'),
    path('api/cambiar-estado-sesion/', cambiar_estado_sesion_api, name='cambiar_estado_sesion_api'),
    path('api/reagendar-sesion/', reagendar_sesion_api, name='reagendar_sesion_api'),
    path('api/disponibilidad/', listar_disponibilidad_api, name='listar_disponibilidad_api'),
    path('api/agregar-disponibilidad/', agregar_disponibilidad_api, name='agregar_disponibilidad_api'),
    path('api/eliminar-disponibilidad/<int:bloque_id>/', eliminar_disponibilidad_api, name='eliminar_disponibilidad_api'),

    path('api/guardar-nota/', guardar_nota_api, name='guardar_nota_api'),
    path('api/nota-sesion/<int:sesion_id>/', obtener_nota_api, name='obtener_nota_api'),

    path('api/chat/contactos/', obtener_contactos_chat_api, name='obtener_contactos_chat_api'),
    path('api/chat/mensajes/<int:contacto_id>/', listar_mensajes_api, name='listar_mensajes_api'),
    path('api/chat/enviar/', enviar_mensaje_api, name='enviar_mensaje_api'),

    path('demo/', demo_movil, name='demo_movil'),

    path('api/animo-hoy/', animo_hoy_api, name='animo_hoy_api'),
    path('api/registrar-animo/', registrar_animo_api, name='registrar_animo_api'),
    path('api/notificaciones/', notificaciones_api, name='notificaciones_api'),
    path('api/notificaciones/marcar/', notificaciones_marcar_api, name='notificaciones_marcar_api'),

    # Resources (public + private share the same DB)
    path('api/resources/', lista_recursos_api, name='lista_recursos_api'),
    path('api/resources/<int:resource_id>/', detalle_recurso_api, name='detalle_recurso_api'),
    path('api/inspiracion-diaria/', inspiracion_diaria_api, name='inspiracion_diaria_api'),
    path('resources/', recursos_publicos, name='recursos_publicos'),
    path('resources/<int:resource_id>/', recurso_detalle, name='recurso_detalle'),
]
