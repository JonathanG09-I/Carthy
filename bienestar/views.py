from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.conf import settings
from django.views.decorators.csrf import ensure_csrf_cookie
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from datetime import datetime, timedelta
import json
import base64
import hashlib
import hmac
import secrets
import re
from cryptography.fernet import Fernet, InvalidToken
from .models import (
    Sesion, Usuario, Disponibilidad, NotaSegura, Mensaje, RegistroAnimo, PasswordResetToken,
    SolicitudProfesional,
)
# Nombre: letras (incluye acentos), espacios, guiones y apóstrofes.
# Exige al menos nombre y apellido; bloquea emojis, números y símbolos.
NOMBRE_COMPLETO_REGEX = re.compile(
    r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+(?:[ '-][A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+)+$"
)

# Contraseña: solo ASCII imprimible (letras, números y símbolos comunes).
# Bloquea emojis y caracteres Unicode especiales.
PASSWORD_REGEX = re.compile(r'^[\x21-\x7E]+$')


def es_foto_perfil_valida(valor):
    """Only allow clearing or data:image/*;base64,... payloads (blocks javascript: URLs)."""
    if valor is None or valor == '':
        return True
    if not isinstance(valor, str):
        return False
    if len(valor) > 1_400_000:
        return False
    return valor.startswith('data:image/') and ';base64,' in valor[:64]


def parse_aware_datetime(fecha_str, hora_str):
    """Parse UI date + time strings into a timezone-aware datetime."""
    hora_limpia = (hora_str or '').strip().lower()
    time_obj = datetime.strptime(hora_limpia, '%I:%M %p' if 'm' in hora_limpia else '%H:%M')
    hora_24 = time_obj.strftime('%H:%M:%S')
    naive = datetime.strptime(f"{fecha_str} {hora_24}", "%Y-%m-%d %H:%M:%S")
    if timezone.is_naive(naive):
        return timezone.make_aware(naive, timezone.get_current_timezone())
    return naive


def hash_reset_code(code):
    return hashlib.sha256(f'{settings.SECRET_KEY}:{code}'.encode('utf-8')).hexdigest()


def es_nombre_completo_valido(nombre):
    if not nombre or not isinstance(nombre, str):
        return False
    nombre = nombre.strip()
    if len(nombre) < 3 or len(nombre) > 100:
        return False
    return bool(NOMBRE_COMPLETO_REGEX.fullmatch(nombre))


def es_password_valida(password):
    if not password or not isinstance(password, str):
        return False
    if len(password) < 6 or len(password) > 128:
        return False
    return bool(PASSWORD_REGEX.fullmatch(password))


# ---------- Utilidad de cifrado para las notas confidenciales ----------
# Derivamos una clave Fernet válida (32 bytes url-safe base64) a partir del
# SECRET_KEY de Django, para no tener que gestionar una llave separada.
def _obtener_cifrador():
    clave_derivada = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    clave_fernet = base64.urlsafe_b64encode(clave_derivada)
    return Fernet(clave_fernet)


def cifrar_texto(texto_plano):
    f = _obtener_cifrador()
    return f.encrypt(texto_plano.encode('utf-8')).decode('utf-8')


def descifrar_texto(texto_cifrado):
    f = _obtener_cifrador()
    try:
        return f.decrypt(texto_cifrado.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        # Si el contenido no está cifrado (notas viejas guardadas antes de este cambio)
        # o la clave no coincide, devolvemos el texto tal cual en vez de reventar.
        return texto_cifrado

# Landing pública (cara de la marca) — home.html
@ensure_csrf_cookie
def home(request):
    """
    Página de inicio pública de Carthy (home.html).
    Presenta la plataforma e invita a crear cuenta o iniciar sesión.
    """
    return render(request, 'home.html')


# SPA autenticada (login / dashboard) — index.html
@ensure_csrf_cookie
def app(request):
    """
    Renderiza index.html con login y dashboard de Carthy.
    Sets the CSRF cookie so SPA fetch POSTs can succeed.
    """
    return render(request, 'index.html')

# API de listado de sesiones con filtrado inteligente por rol y usuario
def lista_sesiones_api(request):
    """
    Retorna un JSON con las sesiones agendadas del usuario autenticado.
    Filtra automáticamente según el rol de la sesión de Django actual
    (no confía en datos enviados por el cliente).
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    user = request.user
    sesiones = Sesion.objects.all()

    if user.rol == 'escuchador':
        sesiones = sesiones.filter(escuchador=user)
    elif user.rol == 'estudiante':
        sesiones = sesiones.filter(estudiante=user)
    # Si es 'admin', no se filtra: puede ver todas las sesiones.

    datos = []
    for s in sesiones:
            datos.append({
            'id': s.id,
            'estudiante': s.estudiante.get_full_name() if s.estudiante.get_full_name() else s.estudiante.username,
            'escuchador': s.escuchador.get_full_name() if s.escuchador.get_full_name() else s.escuchador.username,
            # ISO for client-side locale formatting; fecha_hora kept as English fallback
            'fecha_hora_iso': timezone.localtime(s.fecha_hora).isoformat(),
            'fecha_hora': timezone.localtime(s.fecha_hora).strftime('%B %d, %I:%M %p'),
            'estado': s.get_estado_display(),
            'estado_raw': s.estado,
            'modalidad': s.get_modalidad_display(),
            'modalidad_raw': s.modalidad,
        })

    return JsonResponse({'sesiones': datos}, safe=False, json_dumps_params={'ensure_ascii': False})


# API para que el escuchador cambie el estado de una sesión (confirmar / finalizar)
def cambiar_estado_sesion_api(request):
    """
    Permite al escuchador asignado a una sesión cambiar su estado
    (por ejemplo: pendiente -> confirmada, confirmada -> completada).
    Solo el escuchador dueño de la sesión (o un admin) puede hacerlo.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body)
        sesion_id = data.get('sesion_id')
        nuevo_estado = data.get('nuevo_estado')

        estados_permitidos = dict(Sesion.ESTADOS_CHOICES).keys()
        if nuevo_estado not in estados_permitidos:
            return JsonResponse({'status': 'error', 'message': 'Invalid status.'}, status=400)

        try:
            sesion = Sesion.objects.get(id=sesion_id)
        except Sesion.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)

        es_dueno_escuchador = (sesion.escuchador_id == request.user.id)
        es_dueno_estudiante = (sesion.estudiante_id == request.user.id)
        es_admin = (request.user.rol == 'admin' or request.user.is_superuser)

        # Caso especial: si la sesión está en "reagendada" (el escuchador propuso un nuevo horario),
        # es el ESTUDIANTE quien debe aprobar o rechazar el cambio, no el escuchador.
        if sesion.estado == 'reagendada':
            permitido = es_dueno_estudiante or es_admin
        else:
            permitido = es_dueno_escuchador or es_admin

        if not permitido:
            return JsonResponse({'status': 'error', 'message': 'You are not authorized to modify this session.'}, status=403)

        # Transiciones válidas: no se puede "revivir" una sesión cancelada, por ejemplo
        transiciones_validas = {
            'pendiente': ['confirmada', 'cancelada'],
            'confirmada': ['completada', 'cancelada'],
            'reagendada': ['confirmada', 'cancelada'],
            'completada': [],
            'cancelada': [],
        }
        if nuevo_estado not in transiciones_validas.get(sesion.estado, []):
            return JsonResponse({
                'status': 'error',
                'message': f'Cannot change status from "{sesion.estado}" to "{nuevo_estado}".'
            }, status=400)

        sesion.estado = nuevo_estado
        sesion.save()

        return JsonResponse({'status': 'success', 'message': 'Session status updated.', 'nuevo_estado': nuevo_estado})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# API para que el escuchador proponga un nuevo horario para una sesión existente
def reagendar_sesion_api(request):
    """
    Permite al escuchador dueño de una sesión (o un admin) cambiar su fecha/hora.
    La sesión pasa a estado 'reagendada', quedando pendiente de que el ESTUDIANTE
    apruebe o rechace el nuevo horario propuesto (ver cambiar_estado_sesion_api).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body)
        sesion_id = data.get('sesion_id')
        fecha_str = data.get('fecha')  # Formato: YYYY-MM-DD
        hora_str = data.get('hora')    # Formato: "9:00 am" o "3:30 pm"

        if not sesion_id or not fecha_str or not hora_str:
            return JsonResponse({'status': 'error', 'message': 'Session, date and time are required.'}, status=400)

        try:
            sesion = Sesion.objects.get(id=sesion_id)
        except Sesion.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)

        es_dueno = (sesion.escuchador_id == request.user.id)
        es_admin = (request.user.rol == 'admin' or request.user.is_superuser)
        if not (es_dueno or es_admin):
            return JsonResponse({'status': 'error', 'message': 'You are not authorized to reschedule this session.'}, status=403)

        if sesion.estado not in ('pendiente', 'confirmada'):
            return JsonResponse({
                'status': 'error',
                'message': f'A session in "{sesion.estado}" status cannot be rescheduled.'
            }, status=400)

        # Parsear la nueva fecha/hora (timezone-aware)
        try:
            nueva_fecha_hora = parse_aware_datetime(fecha_str, hora_str)
        except ValueError:
            return JsonResponse({'status': 'error', 'message': 'Invalid date or time format.'}, status=400)

        # Validar colisión con otra cita del mismo escuchador (excluyendo esta misma sesión)
        colision = Sesion.objects.filter(
            escuchador=sesion.escuchador,
            fecha_hora=nueva_fecha_hora
        ).exclude(id=sesion.id).exclude(estado='cancelada').exists()

        if colision:
            return JsonResponse({
                'status': 'error',
                'message': 'You already have another session booked at that date and time.'
            }, status=409)

        # Validar disponibilidad configurada (si existe alguna) del escuchador
        if Disponibilidad.objects.filter(escuchador=sesion.escuchador).exists():
            hora_cita = nueva_fecha_hora.time()
            dia_semana_cita = nueva_fecha_hora.weekday()

            dentro_de_horario = Disponibilidad.objects.filter(
                escuchador=sesion.escuchador,
                dia_semana=dia_semana_cita,
                hora_inicio__lte=hora_cita,
                hora_fin__gt=hora_cita
            ).exists()

            if not dentro_de_horario:
                return JsonResponse({
                    'status': 'error',
                    'message': 'That new date/time falls outside your configured availability.'
                }, status=400)

        sesion.fecha_hora = nueva_fecha_hora
        sesion.estado = 'reagendada'
        sesion.save()

        return JsonResponse({
            'status': 'success',
            'message': 'New time proposed. Waiting for the student to approve it.'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# API para obtener psicólogos activos en el sistema
def obtener_psicologos_api(request):
    """
    Retorna un JSON con la lista de usuarios con el rol de psicólogo ('escuchador').
    Se utiliza para llenar el selector dinámico del agendamiento.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    psicologos = Usuario.objects.filter(rol='escuchador', is_active=True)
    datos = []
    for p in psicologos:
        foto = p.foto_url if p.foto_url and str(p.foto_url).startswith('data:image/') else ''
        datos.append({
            'id': p.id,
            'nombre_completo': p.get_full_name() if p.get_full_name() else p.username,
            'username': p.username,
            'foto_url': foto,
        })
    return JsonResponse(datos, safe=False, json_dumps_params={'ensure_ascii': False})

# API para crear sesiones reales en la base de datos
def crear_sesion_api(request):
    """
    Recibe la información de la cita, parsea la fecha y hora seleccionada,
    y asocia la sesión al estudiante y psicólogo correspondientes.
    """
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

        try:
            data = json.loads(request.body)
            psicologo_id = data.get('psicologo_id')
            fecha_str = data.get('fecha')  # Formato: YYYY-MM-DD
            hora_str = data.get('hora')    # Formato: "9:00 am" o "3:30 pm"
            modalidad = data.get('modalidad', 'virtual').lower()

            if not fecha_str or not hora_str:
                return JsonResponse({'status': 'error', 'message': 'Please complete all required fields.'}, status=400)

            # 1. El estudiante es siempre el usuario autenticado por la sesión
            estudiante = request.user

            # 2. Buscar al Psicólogo seleccionado o asignar el primero disponible si es 'Any available'
            if not psicologo_id or psicologo_id == 'any':
                psicologo = Usuario.objects.filter(rol='escuchador').first()
                if not psicologo:
                    return JsonResponse({'status': 'error', 'message': 'No psychologists currently registered in the system.'}, status=404)
            else:
                try:
                    psicologo = Usuario.objects.get(id=psicologo_id, rol='escuchador', is_active=True)
                except Usuario.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Selected psychologist not found.'}, status=404)

            # 3-4. Parse date/time into timezone-aware datetime
            try:
                fecha_hora_final = parse_aware_datetime(fecha_str, hora_str)
            except ValueError:
                return JsonResponse({'status': 'error', 'message': 'Invalid date or time format.'}, status=400)

            # 5. Validar que el psicólogo no tenga ya una cita en ese mismo horario
            colision = Sesion.objects.filter(
                escuchador=psicologo,
                fecha_hora=fecha_hora_final
            ).exclude(estado='cancelada').exists()

            if colision:
                return JsonResponse({
                    'status': 'error',
                    'message': 'This psychologist is already booked at that date and time. Please choose another slot.'
                }, status=409)

            # 6. Validar que la fecha/hora caiga dentro de un bloque de disponibilidad del escuchador.
            # Si el escuchador todavía no configuró ninguna disponibilidad, no se bloquea
            # (comportamiento de transición, para no romper cuentas ya existentes sin horarios definidos).
            if Disponibilidad.objects.filter(escuchador=psicologo).exists():
                # Use local time components for availability matching
                local_dt = timezone.localtime(fecha_hora_final)
                hora_cita = local_dt.time()
                dia_semana_cita = local_dt.weekday()  # 0=Lunes ... 6=Domingo

                dentro_de_horario = Disponibilidad.objects.filter(
                    escuchador=psicologo,
                    dia_semana=dia_semana_cita,
                    hora_inicio__lte=hora_cita,
                    hora_fin__gt=hora_cita
                ).exists()

                if not dentro_de_horario:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'This psychologist is not available at that day/time. Please choose a time within their availability.'
                    }, status=400)

            # 7. Crear el registro real de la sesión en la base de datos
            nueva_sesion = Sesion.objects.create(
                estudiante=estudiante,
                escuchador=psicologo,
                fecha_hora=fecha_hora_final,
                modalidad=modalidad,
                estado='pendiente' # Se guarda con estado Pendiente por defecto
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Your session has been successfully booked!'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)


# Autenticación segura para el inicio de sesión (Login)
def login_api(request):
    """
    Procesa las credenciales de inicio de sesión de manera segura.
    Soporta autenticación usando tanto el nombre de usuario como el correo electrónico.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username_or_email = data.get('username')
            password = data.get('password')
            
            username = username_or_email
            
            # Si el usuario ingresó un correo electrónico, buscamos su nombre de usuario correspondiente
            if '@' in username_or_email:
                try:
                    usuario_encontrado = Usuario.objects.get(email__iexact=username_or_email)
                    username = usuario_encontrado.username
                except Usuario.DoesNotExist:
                    return JsonResponse({'status': 'error', 'message': 'Email address not registered.'}, status=400)

            # Autenticación nativa y segura de Django
            user = authenticate(username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    # Crear la sesión real de Django (cookie de sesión segura)
                    login(request, user)

                    return JsonResponse({
                        'status': 'success',
                        'user': {
                            'id': user.id,
                            'username': user.username,
                            'nombre_completo': user.get_full_name() if user.get_full_name() else user.username,
                            'email': user.email,
                            'rol': user.get_rol_display() if hasattr(user, 'get_rol_display') else 'Student',
                            'rol_raw': user.rol if hasattr(user, 'rol') else 'estudiante',
                            'foto_url': user.foto_url if (hasattr(user, 'foto_url') and user.foto_url) else ''
                        }
                    })
                else:
                    return JsonResponse({'status': 'error', 'message': 'This account has been deactivated.'}, status=400)
            else:
                return JsonResponse({'status': 'error', 'message': 'Incorrect username/email or password.'}, status=400)
                
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

# API para verificar si hay una sesión de Django activa (al recargar la página)
def sesion_actual_api(request):
    """
    Devuelve los datos del usuario autenticado si existe una sesión activa.
    Se usa al cargar index.html para decidir si mostrar el login
    o restaurar directamente el dashboard, sin pedir credenciales de nuevo.
    """
    if request.user.is_authenticated:
        user = request.user
        return JsonResponse({
            'status': 'success',
            'user': {
                'id': user.id,
                'username': user.username,
                'nombre_completo': user.get_full_name() if user.get_full_name() else user.username,
                'email': user.email,
                'rol': user.get_rol_display() if hasattr(user, 'get_rol_display') else 'Student',
                'rol_raw': user.rol if hasattr(user, 'rol') else 'estudiante',
                'foto_url': user.foto_url if (hasattr(user, 'foto_url') and user.foto_url) else ''
            }
        })
    return JsonResponse({'status': 'error', 'message': 'No active session.'}, status=401)

# Registro público: solo crea cuentas de estudiantes
def registro_api(request):
    """
    Registra cuentas públicas de estudiantes encriptando su contraseña.
    El rol se determina exclusivamente en el servidor para impedir la
    elevación de privilegios mediante datos manipulados desde el cliente.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            nombre_completo = data.get('nombre_completo')
            if not username or not email or not password or not nombre_completo:
                return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)

            nombre_completo = nombre_completo.strip()
            if not es_nombre_completo_valido(nombre_completo):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Full name may only contain letters, spaces, hyphens or apostrophes. Emojis and special characters are not allowed.'
                }, status=400)

            if len(password) < 6:
                return JsonResponse({'status': 'error', 'message': 'Password must be at least 6 characters long.'}, status=400)

            if not es_password_valida(password):
                return JsonResponse({
                    'status': 'error',
                    'message': 'Password may only contain letters, numbers and common symbols. Emojis are not allowed.'
                }, status=400)

            if Usuario.objects.filter(username=username).exists():
                return JsonResponse({'status': 'error', 'message': 'Username is already in use.'}, status=400)

            if Usuario.objects.filter(email__iexact=email).exists():
                return JsonResponse({'status': 'error', 'message': 'This email is already registered.'}, status=400)

            # Dividimos el nombre completo para guardarlo ordenadamente en first_name y last_name de Django
            partes = nombre_completo.split(' ', 1)
            first_name = partes[0]
            last_name = partes[1] if len(partes) > 1 else ''

            # Creamos el usuario encriptando la contraseña automáticamente
            nuevo_usuario = Usuario.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                rol='estudiante',
            )

            return JsonResponse({
                'status': 'success',
                'message': 'Account created successfully! You can now Sign In.'
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)


def crear_solicitud_profesional_api(request):
    """Create a pending professional-account request without changing any user role."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        nombre_completo = (data.get('nombre_completo') or '').strip()
        email = (data.get('email') or '').strip().lower()
        telefono = (data.get('telefono') or '').strip()
        profesion = (data.get('profesion') or '').strip()
        especialidad = (data.get('especialidad') or '').strip()
        institucion = (data.get('institucion') or '').strip()
        informacion_adicional = (data.get('informacion_adicional') or '').strip()

        if not nombre_completo or not email or not profesion:
            return JsonResponse({'status': 'error', 'message': 'Full name, email and profession are required.'}, status=400)
        if not es_nombre_completo_valido(nombre_completo):
            return JsonResponse({'status': 'error', 'message': 'Please enter a valid full name.'}, status=400)
        try:
            validate_email(email)
        except ValidationError:
            return JsonResponse({'status': 'error', 'message': 'Please enter a valid email address.'}, status=400)
        if len(profesion) > 120 or len(especialidad) > 120 or len(institucion) > 160 or len(telefono) > 30:
            return JsonResponse({'status': 'error', 'message': 'One or more fields are too long.'}, status=400)
        if len(informacion_adicional) > 2000:
            return JsonResponse({'status': 'error', 'message': 'Additional information must be 2000 characters or fewer.'}, status=400)

        if SolicitudProfesional.objects.filter(email__iexact=email, estado='pendiente').exists():
            return JsonResponse({'status': 'error', 'message': 'A professional account request for this email is already pending review.'}, status=409)

        usuario_existente = Usuario.objects.filter(email__iexact=email).first()
        if usuario_existente and usuario_existente.rol in ('escuchador', 'admin'):
            return JsonResponse({'status': 'error', 'message': 'This email already has a professional or administrative account.'}, status=409)

        solicitud = SolicitudProfesional.objects.create(
            nombre_completo=nombre_completo,
            email=email,
            telefono=telefono,
            profesion=profesion,
            especialidad=especialidad,
            institucion=institucion,
            informacion_adicional=informacion_adicional,
            estado='pendiente',
        )
        return JsonResponse({
            'status': 'success',
            'message': 'Professional account request submitted successfully.',
            'request_id': solicitud.id,
        }, status=201)
    except (TypeError, json.JSONDecodeError):
        return JsonResponse({'status': 'error', 'message': 'Invalid request data.'}, status=400)


def recuperar_password_api(request):
    """
    Two-step password reset with a one-time verification code.
    Step 1 (action=request): username + email must match the same account → issues a code.
    Step 2 (action=confirm): username + email + code + new password → updates password.

    Without SMTP, the code is returned only when DEBUG=True (local/demo).
    In production the same API shape is ready for email delivery later.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    try:
        data = json.loads(request.body)
        action = (data.get('action') or 'confirm').strip().lower()
        email = (data.get('email') or '').strip().lower()
        username = (data.get('username') or '').strip()

        if action == 'request':
            if not email or not username:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Username and email are required to request a reset code.'
                }, status=400)

            generic = {
                'status': 'success',
                'message': 'If the account exists, a verification code was generated. Enter it to set a new password.',
                'step': 'confirm',
            }

            try:
                usuario = Usuario.objects.get(username__iexact=username, email__iexact=email, is_active=True)
            except Usuario.DoesNotExist:
                # Do not reveal whether the account exists
                return JsonResponse(generic)

            # Invalidate previous unused tokens
            PasswordResetToken.objects.filter(usuario=usuario, used_at__isnull=True).update(
                used_at=timezone.now()
            )

            code = f'{secrets.randbelow(1_000_000):06d}'
            PasswordResetToken.objects.create(
                usuario=usuario,
                code_hash=hash_reset_code(code),
                expires_at=timezone.now() + timedelta(minutes=15),
            )

            if settings.DEBUG:
                generic['dev_reset_code'] = code
                generic['message'] = (
                    'Verification code generated (DEBUG only shown here). '
                    'Enter the code with your new password.'
                )
            return JsonResponse(generic)

        # --- confirm ---
        password = data.get('password') or ''
        password_confirm = data.get('password_confirm') or ''
        code = (data.get('code') or '').strip()

        if not email or not username or not code or not password or not password_confirm:
            return JsonResponse({'status': 'error', 'message': 'All fields are required.'}, status=400)

        if password != password_confirm:
            return JsonResponse({'status': 'error', 'message': 'Passwords do not match.'}, status=400)

        if not es_password_valida(password):
            return JsonResponse({
                'status': 'error',
                'message': 'Password may only contain letters, numbers and common symbols. Emojis are not allowed.'
            }, status=400)

        try:
            usuario = Usuario.objects.get(username__iexact=username, email__iexact=email, is_active=True)
        except Usuario.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Invalid reset request.'}, status=400)

        token = (
            PasswordResetToken.objects
            .filter(usuario=usuario, used_at__isnull=True, expires_at__gt=timezone.now())
            .order_by('-created_at')
            .first()
        )
        if not token or not hmac.compare_digest(token.code_hash, hash_reset_code(code)):
            return JsonResponse({'status': 'error', 'message': 'Invalid or expired verification code.'}, status=400)

        usuario.set_password(password)
        usuario.save(update_fields=['password'])
        token.used_at = timezone.now()
        token.save(update_fields=['used_at'])

        return JsonResponse({
            'status': 'success',
            'message': 'Password updated successfully. You can now sign in.'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def logout_api(request):
    """Ends the Django session on the server (not just hiding the SPA)."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)
    logout(request)
    return JsonResponse({'status': 'success', 'message': 'Signed out successfully.'})


def demo_movil(request):
    return render(request, 'demo_movil.html')


# API para guardar o actualizar la nota privada de una sesión (solo escuchadores)
def guardar_nota_api(request):
    """
    Crea o actualiza la nota confidencial asociada a una sesión.
    Solo el escuchador asignado a esa sesión (o un admin) puede escribir la nota.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body)
        sesion_id = data.get('sesion_id')
        contenido = data.get('contenido', '').strip()

        if not sesion_id or not contenido:
            return JsonResponse({'status': 'error', 'message': 'Session and content are required.'}, status=400)

        try:
            sesion = Sesion.objects.get(id=sesion_id)
        except Sesion.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)

        # Solo el escuchador dueño de la sesión (o un admin) puede escribir la nota
        es_dueno = (sesion.escuchador_id == request.user.id)
        es_admin = (request.user.rol == 'admin' or request.user.is_superuser)
        if not (es_dueno or es_admin):
            return JsonResponse({'status': 'error', 'message': 'You are not authorized to write a note for this session.'}, status=403)

        nota, creada = NotaSegura.objects.update_or_create(
            sesion=sesion,
            defaults={
                'autor': request.user,
                'contenido_encriptado': cifrar_texto(contenido),
            }
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Note saved successfully.' if creada else 'Note updated successfully.'
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# API para leer la nota privada de una sesión (solo el escuchador dueño o admin)
def obtener_nota_api(request, sesion_id):
    """
    Devuelve la nota confidencial de una sesión.
    Solo visible para el escuchador asignado a esa sesión, o un admin.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        sesion = Sesion.objects.get(id=sesion_id)
    except Sesion.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Session not found.'}, status=404)

    es_dueno = (sesion.escuchador_id == request.user.id)
    es_admin = (request.user.rol == 'admin' or request.user.is_superuser)
    if not (es_dueno or es_admin):
        return JsonResponse({'status': 'error', 'message': 'You are not authorized to view this note.'}, status=403)

    try:
        nota = sesion.nota_segura
        return JsonResponse({
            'status': 'success',
            'contenido': descifrar_texto(nota.contenido_encriptado),
            'ultima_modificacion': nota.ultima_modificacion.strftime('%B %d, %Y %I:%M %p')
        })
    except NotaSegura.DoesNotExist:
        return JsonResponse({'status': 'success', 'contenido': '', 'ultima_modificacion': None})

# API para que el usuario autenticado actualice su propio perfil
def actualizar_perfil_api(request):
    """
    Permite al usuario logueado actualizar su nombre completo y correo.
    Solo puede modificar su propia cuenta (nunca la de otro usuario).
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body)
        nombre_completo = data.get('nombre_completo', '').strip()
        email = data.get('email', '').strip()
        foto_base64 = data.get('foto_base64', None)

        if not nombre_completo or not email:
            return JsonResponse({'status': 'error', 'message': 'Full name and email are required.'}, status=400)

        if not es_nombre_completo_valido(nombre_completo):
            return JsonResponse({
                'status': 'error',
                'message': 'Full name may only contain letters, spaces, hyphens or apostrophes. Emojis and special characters are not allowed.'
            }, status=400)

        # Límite / validación de foto de perfil (solo data:image Base64 o vacío)
        if foto_base64 is not None and not es_foto_perfil_valida(foto_base64):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid profile image. Upload a PNG/JPG under 1MB.'
            }, status=400)

        if foto_base64 and len(foto_base64) > 1_400_000:
            return JsonResponse({'status': 'error', 'message': 'Image is too large. Please use an image under 1MB.'}, status=400)

        # Si cambia el email, verificar que no esté en uso por OTRO usuario
        if Usuario.objects.filter(email__iexact=email).exclude(id=request.user.id).exists():
            return JsonResponse({'status': 'error', 'message': 'This email is already in use by another account.'}, status=400)

        partes = nombre_completo.split(' ', 1)
        request.user.first_name = partes[0]
        request.user.last_name = partes[1] if len(partes) > 1 else ''
        request.user.email = email
        if foto_base64 is not None:
            request.user.foto_url = foto_base64 or None
        request.user.save()

        return JsonResponse({
            'status': 'success',
            'message': 'Profile updated successfully.',
            'user': {
                'nombre_completo': request.user.get_full_name() if request.user.get_full_name() else request.user.username,
                'email': request.user.email,
                'foto_url': request.user.foto_url or '',
            }
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def cambiar_password_api(request):
    """
    Permite al usuario autenticado cambiar su contraseña (perfil / Settings).
    Requiere la contraseña actual y confirmación de la nueva.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body)
        actual = data.get('password_actual') or data.get('current_password') or ''
        nueva = data.get('password_nueva') or data.get('new_password') or ''
        confirm = data.get('password_confirm') or data.get('confirm_password') or ''

        if not actual or not nueva or not confirm:
            return JsonResponse({'status': 'error', 'message': 'All password fields are required.', 'code': 'missing'}, status=400)

        if not request.user.check_password(actual):
            return JsonResponse({'status': 'error', 'message': 'Current password is incorrect.', 'code': 'wrong_current'}, status=400)

        if nueva != confirm:
            return JsonResponse({'status': 'error', 'message': 'New passwords do not match.', 'code': 'mismatch'}, status=400)

        if len(nueva) < 6:
            return JsonResponse({'status': 'error', 'message': 'Password must be at least 6 characters.', 'code': 'too_short'}, status=400)

        # Block emoji / non-printable junk (same spirit as registration)
        if any(ord(ch) > 0xFFFF for ch in nueva) or any(0x1F300 <= ord(ch) <= 0x1FAFF for ch in nueva):
            return JsonResponse({'status': 'error', 'message': 'Password cannot include emojis.', 'code': 'invalid'}, status=400)

        request.user.set_password(nueva)
        request.user.save()
        # Keep the user logged in after password change
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)

        return JsonResponse({'status': 'success', 'message': 'Password updated successfully.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


def dashboard_resumen_api(request):
    """
    Resumen real para el dashboard (especialmente Psych.):
    estudiantes del mes, sesiones completadas/pendientes, horas de disponibilidad semanal.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    ahora = timezone.localtime()
    citas = Sesion.objects.all()
    if request.user.rol == 'estudiante':
        citas = citas.filter(estudiante=request.user)
    elif request.user.rol == 'escuchador':
        citas = citas.filter(escuchador=request.user)

    hoy = timezone.localdate()
    sesiones_hoy = citas.filter(fecha_hora__date=hoy).exclude(estado='cancelada').count()
    pendientes = citas.filter(estado='pendiente').count()
    completadas = citas.filter(estado='completada').count()

    estudiantes_mes = 0
    horas_disponibles = 0.0
    if request.user.rol == 'escuchador':
        mes_qs = Sesion.objects.filter(
            escuchador=request.user,
            fecha_hora__year=ahora.year,
            fecha_hora__month=ahora.month,
        ).exclude(estado='cancelada')
        estudiantes_mes = mes_qs.values('estudiante_id').distinct().count()

        total_seconds = 0.0
        for b in Disponibilidad.objects.filter(escuchador=request.user):
            start = datetime.combine(hoy, b.hora_inicio)
            end = datetime.combine(hoy, b.hora_fin)
            delta = (end - start).total_seconds()
            if delta > 0:
                total_seconds += delta
        horas_disponibles = round(total_seconds / 3600.0, 1)

    return JsonResponse({
        'status': 'success',
        'sesiones_hoy': sesiones_hoy,
        'pendientes': pendientes,
        'completadas': completadas,
        'estudiantes_mes': estudiantes_mes,
        'horas_disponibles': horas_disponibles,
        'bloques_disponibilidad': Disponibilidad.objects.filter(escuchador=request.user).count()
            if request.user.rol == 'escuchador' else 0,
    })


# API para que el escuchador vea sus propios bloques de disponibilidad
def listar_disponibilidad_api(request):
    """
    Devuelve los bloques de disponibilidad del escuchador autenticado.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    bloques = Disponibilidad.objects.filter(escuchador=request.user)
    datos = [{
        'id': b.id,
        'dia_semana': b.dia_semana,
        'dia_nombre': b.get_dia_semana_display(),
        'hora_inicio': b.hora_inicio.strftime('%H:%M'),
        'hora_fin': b.hora_fin.strftime('%H:%M'),
    } for b in bloques]

    return JsonResponse({'status': 'success', 'bloques': datos})


# API para que el escuchador agregue un nuevo bloque de disponibilidad
def agregar_disponibilidad_api(request):
    """
    Crea un nuevo bloque de disponibilidad para el escuchador autenticado.
    Solo escuchadores pueden usar este endpoint.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    if request.user.rol != 'escuchador':
        return JsonResponse({'status': 'error', 'message': 'Only listeners can configure availability.'}, status=403)

    try:
        data = json.loads(request.body)
        dia_semana = data.get('dia_semana')
        hora_inicio = data.get('hora_inicio')  # formato "HH:MM"
        hora_fin = data.get('hora_fin')        # formato "HH:MM"

        if dia_semana is None or not hora_inicio or not hora_fin:
            return JsonResponse({'status': 'error', 'message': 'Day, start time and end time are required.'}, status=400)

        dia_semana = int(dia_semana)
        if dia_semana < 0 or dia_semana > 6:
            return JsonResponse({'status': 'error', 'message': 'Invalid day of week.'}, status=400)

        hora_inicio_obj = datetime.strptime(hora_inicio, '%H:%M').time()
        hora_fin_obj = datetime.strptime(hora_fin, '%H:%M').time()

        if hora_fin_obj <= hora_inicio_obj:
            return JsonResponse({'status': 'error', 'message': 'End time must be after start time.'}, status=400)

        nuevo_bloque = Disponibilidad.objects.create(
            escuchador=request.user,
            dia_semana=dia_semana,
            hora_inicio=hora_inicio_obj,
            hora_fin=hora_fin_obj
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Availability block added.',
            'bloque': {
                'id': nuevo_bloque.id,
                'dia_nombre': nuevo_bloque.get_dia_semana_display(),
                'hora_inicio': nuevo_bloque.hora_inicio.strftime('%H:%M'),
                'hora_fin': nuevo_bloque.hora_fin.strftime('%H:%M'),
            }
        })

    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Invalid time format. Use HH:MM.'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# API para que el escuchador elimine uno de sus propios bloques de disponibilidad
def eliminar_disponibilidad_api(request, bloque_id):
    """
    Elimina un bloque de disponibilidad. Solo el escuchador dueño del bloque puede borrarlo.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        bloque = Disponibilidad.objects.get(id=bloque_id)
    except Disponibilidad.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Availability block not found.'}, status=404)

    if bloque.escuchador_id != request.user.id:
        return JsonResponse({'status': 'error', 'message': 'You are not authorized to delete this block.'}, status=403)

    bloque.delete()
    return JsonResponse({'status': 'success', 'message': 'Availability block removed.'})


# ---------- Wellbeing Chat: contactos, mensajes y envío ----------

def _usuarios_pueden_chatear(usuario_a, usuario_b):
    """
    Regla de negocio: un estudiante puede chatear con cualquier escuchador.
    Un escuchador solo puede chatear con estudiantes que le hayan agendado
    al menos una sesión real (protege su privacidad laboral).
    Admins pueden chatear con cualquiera.
    """
    if usuario_a.rol == 'admin' or usuario_b.rol == 'admin' or usuario_a.is_superuser or usuario_b.is_superuser:
        return True

    if usuario_a.rol == 'estudiante' and usuario_b.rol == 'escuchador':
        return True
    if usuario_a.rol == 'escuchador' and usuario_b.rol == 'estudiante':
        return Sesion.objects.filter(escuchador=usuario_a, estudiante=usuario_b).exists()

    return False


# API para listar los contactos disponibles para chatear, según el rol
def obtener_contactos_chat_api(request):
    """
    Estudiante: ve a todos los escuchadores registrados.
    Escuchador: ve solo a los estudiantes que le han agendado al menos una cita real.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    if request.user.rol == 'estudiante':
        contactos_qs = Usuario.objects.filter(rol='escuchador')
    elif request.user.rol == 'escuchador':
        ids_estudiantes = Sesion.objects.filter(escuchador=request.user).values_list('estudiante_id', flat=True).distinct()
        contactos_qs = Usuario.objects.filter(id__in=ids_estudiantes)
    else:
        # Admin u otro rol: ve a todos los usuarios (menos a sí mismo)
        contactos_qs = Usuario.objects.exclude(id=request.user.id)

    datos = [{
        'id': c.id,
        'username': c.username,
        'nombre_completo': c.get_full_name() if c.get_full_name() else c.username,
        'rol': c.get_rol_display(),
        'rol_raw': c.rol,
        'foto_url': c.foto_url or '',
    } for c in contactos_qs]

    return JsonResponse({'status': 'success', 'contactos': datos})


# API para listar el historial de mensajes entre el usuario autenticado y un contacto
def listar_mensajes_api(request, contacto_id):
    """
    Devuelve la conversación entre el usuario autenticado y el contacto indicado,
    solo si la relación entre ambos está permitida por las reglas de chat.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        contacto = Usuario.objects.get(id=contacto_id)
    except Usuario.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Contact not found.'}, status=404)

    if not _usuarios_pueden_chatear(request.user, contacto):
        return JsonResponse({'status': 'error', 'message': 'You are not authorized to chat with this contact.'}, status=403)

    # Solo mensajes entre estos dos usuarios (no incluir emisor==receptor,
    # que filtraba mal y filtraba mensajes "a sí mismo" del contacto a todos).
    mensajes = Mensaje.objects.filter(
        Q(emisor=request.user, receptor=contacto) |
        Q(emisor=contacto, receptor=request.user)
    ).order_by('creado_en')

    # Al abrir esta conversación, marcamos como leídos los mensajes que este contacto
    # nos envió y todavía no habíamos visto (afecta el contador de notificaciones).
    Mensaje.objects.filter(emisor=contacto, receptor=request.user, leido=False).update(leido=True)

    datos = [{
        'emisor_id': m.emisor_id,
        'contenido': m.contenido,
        'creado_en': m.creado_en.strftime('%I:%M %p'),
        'creado_en_iso': m.creado_en.isoformat(),
        'leido': m.leido,
        'es_mio': m.emisor_id == request.user.id,
    } for m in mensajes]

    return JsonResponse({'status': 'success', 'mensajes': datos})


# API para enviar un nuevo mensaje de chat
def enviar_mensaje_api(request):
    """
    Crea un nuevo mensaje del usuario autenticado hacia un receptor,
    solo si la relación entre ambos está permitida por las reglas de chat.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body)
        receptor_id = data.get('receptor_id')
        contenido = data.get('contenido', '').strip()

        if not receptor_id or not contenido:
            return JsonResponse({'status': 'error', 'message': 'Recipient and content are required.'}, status=400)

        try:
            receptor = Usuario.objects.get(id=receptor_id)
        except Usuario.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Recipient not found.'}, status=404)

        if not _usuarios_pueden_chatear(request.user, receptor):
            return JsonResponse({'status': 'error', 'message': 'You are not authorized to message this contact.'}, status=403)

        Mensaje.objects.create(emisor=request.user, receptor=receptor, contenido=contenido)

        return JsonResponse({'status': 'success', 'message': 'Message sent.'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


# ---------- Mood Tracker: registro de ánimo diario ----------

CONSEJOS_POR_ANIMO = {
    'genial': "That's wonderful to hear! Keep doing what makes you feel this way, and consider sharing your energy with someone else today.",
    'bien': "Glad you're doing well! A short walk or a few minutes of fresh air can help keep that momentum going.",
    'normal': "An okay day is still a day you showed up. Try a short breathing exercise (4-7-8) if you need a small reset.",
    'mal': "It's alright to have a down day. Be gentle with yourself, and remember you can book a session with a listener whenever you need to talk.",
    'enojado': "Frustration is valid. Try stepping away for a few minutes before reacting, and consider writing down what's bothering you.",
}


# API para saber si el estudiante ya registró su ánimo hoy
def animo_hoy_api(request):
    """
    Indica si el estudiante autenticado ya registró su estado de ánimo en la fecha actual.
    Incluye racha de días consecutivos con registro (dato real desde RegistroAnimo).
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    if request.user.rol != 'estudiante':
        return JsonResponse({'status': 'success', 'ya_registrado': True, 'racha_dias': 0})

    hoy = timezone.localdate()
    fechas = set(
        RegistroAnimo.objects.filter(estudiante=request.user)
        .values_list('fecha', flat=True)
    )
    racha = 0
    cursor = hoy
    # If today isn't logged yet, streak is consecutive days ending yesterday
    if hoy not in fechas:
        cursor = hoy - timedelta(days=1)
    while cursor in fechas:
        racha += 1
        cursor = cursor - timedelta(days=1)

    registro = RegistroAnimo.objects.filter(estudiante=request.user, fecha=hoy).first()
    if registro:
        return JsonResponse({
            'status': 'success',
            'ya_registrado': True,
            'animo': registro.animo,
            'consejo': CONSEJOS_POR_ANIMO.get(registro.animo, 'Thanks for sharing how you feel today.'),
            'racha_dias': racha,
        })

    return JsonResponse({'status': 'success', 'ya_registrado': False, 'racha_dias': racha})


# API para guardar el registro de ánimo del día
def registrar_animo_api(request):
    """
    Guarda el estado de ánimo seleccionado por el estudiante para el día de hoy.
    Devuelve un consejo corto y personalizado según el ánimo elegido.
    Protegido por unique_together en el modelo: no se puede registrar dos veces el mismo día.
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    if request.user.rol != 'estudiante':
        return JsonResponse({'status': 'error', 'message': 'Only students can log a daily mood.'}, status=403)

    try:
        data = json.loads(request.body)
        animo = data.get('animo')

        animos_validos = dict(RegistroAnimo.ANIMOS_CHOICES).keys()
        if animo not in animos_validos:
            return JsonResponse({'status': 'error', 'message': 'Invalid mood value.'}, status=400)

        hoy = timezone.localdate()

        if RegistroAnimo.objects.filter(estudiante=request.user, fecha=hoy).exists():
            return JsonResponse({'status': 'error', 'message': 'You already logged your mood today.'}, status=400)

        RegistroAnimo.objects.create(
            estudiante=request.user,
            animo=animo,
            fecha=timezone.localdate(),
        )

        return JsonResponse({
            'status': 'success',
            'message': 'Mood logged successfully.',
            'consejo': CONSEJOS_POR_ANIMO.get(animo, "Thanks for sharing how you feel today.")
        })

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

# ---------- Notificaciones In-App ----------

def notificaciones_api(request):
    """
    Resumen accionable para el usuario autenticado.
    Soporta ?lang=es|en. Cada item tiene id estable para poder descartarlo.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'success', 'total': 0, 'items': []})

    lang = (request.GET.get('lang') or 'en').strip().lower()
    if lang not in ('en', 'es'):
        lang = 'en'

    dismissed = set(request.session.get('notif_dismissed', []))
    items = []

    mensajes_sin_leer = Mensaje.objects.filter(receptor=request.user, leido=False).count()
    if mensajes_sin_leer > 0:
        nid = 'mensaje:unread'
        if nid not in dismissed:
            if lang == 'es':
                texto = f'Tienes {mensajes_sin_leer} mensaje{"s" if mensajes_sin_leer != 1 else ""} sin leer.'
            else:
                texto = f'You have {mensajes_sin_leer} unread message{"s" if mensajes_sin_leer != 1 else ""}.'
            items.append({'id': nid, 'tipo': 'mensaje', 'texto': texto, 'tab': 'tab-chat'})

    if request.user.rol == 'estudiante':
        for s in Sesion.objects.filter(estudiante=request.user, estado='reagendada'):
            nid = f'reagendada:{s.id}'
            if nid in dismissed:
                continue
            name = s.escuchador.get_full_name() or s.escuchador.username
            texto = (
                f'{name} propuso un nuevo horario para tu sesión.'
                if lang == 'es'
                else f'{name} proposed a new time for your session.'
            )
            items.append({'id': nid, 'tipo': 'reagendada', 'texto': texto, 'ref_id': s.id, 'tab': 'tab-sesiones'})

    elif request.user.rol == 'escuchador':
        for s in Sesion.objects.filter(escuchador=request.user, estado='pendiente'):
            nid = f'pendiente:{s.id}'
            if nid in dismissed:
                continue
            name = s.estudiante.get_full_name() or s.estudiante.username
            texto = (
                f'Nueva solicitud de sesión de {name}.'
                if lang == 'es'
                else f'New session request from {name}.'
            )
            items.append({'id': nid, 'tipo': 'pendiente', 'texto': texto, 'ref_id': s.id, 'tab': 'tab-sesiones'})

    return JsonResponse({
        'status': 'success',
        'total': len(items),
        'items': items,
    })


def notificaciones_marcar_api(request):
    """
    POST: marca notificaciones como atendidas.
    body: { "ids": ["mensaje:unread", ...] } o { "all": true }
    """
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Authentication required.'}, status=401)

    try:
        data = json.loads(request.body or '{}')
    except Exception:
        data = {}

    dismissed = set(request.session.get('notif_dismissed', []))
    mark_all = bool(data.get('all'))
    ids = data.get('ids') or []

    if mark_all or 'mensaje:unread' in ids:
        Mensaje.objects.filter(receptor=request.user, leido=False).update(leido=True)

    if mark_all:
        if request.user.rol == 'estudiante':
            for s in Sesion.objects.filter(estudiante=request.user, estado='reagendada'):
                dismissed.add(f'reagendada:{s.id}')
        elif request.user.rol == 'escuchador':
            for s in Sesion.objects.filter(escuchador=request.user, estado='pendiente'):
                dismissed.add(f'pendiente:{s.id}')
        dismissed.add('mensaje:unread')
    else:
        for nid in ids:
            if isinstance(nid, str) and nid:
                dismissed.add(nid)

    request.session['notif_dismissed'] = list(dismissed)
    request.session.modified = True
    return JsonResponse({'status': 'success', 'dismissed': len(dismissed)})
