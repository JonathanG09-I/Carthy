"""Landing contact form — persist messages; do not send email."""
import json
import re
import time

from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import ContactMessage

EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

# Simple abuse protection: max submissions per IP in a sliding window.
CONTACT_RATE_LIMIT = 5
CONTACT_RATE_WINDOW_SEC = 600  # 10 minutes


def _as_text(value, max_len=None):
    """Coerce JSON values to a safe trimmed string (never call .strip on non-str)."""
    if value is None or isinstance(value, (dict, list, bool)):
        return ''
    text = str(value).strip()
    if max_len is not None:
        text = text[:max_len]
    return text


def _client_ip(request):
    forwarded = (request.META.get('HTTP_X_FORWARDED_FOR') or '').split(',')[0].strip()
    return forwarded or request.META.get('REMOTE_ADDR') or 'unknown'


def _rate_limited(ip):
    key = f'contact_rate:{ip}'
    now = time.time()
    stamps = cache.get(key) or []
    stamps = [t for t in stamps if now - t < CONTACT_RATE_WINDOW_SEC]
    if len(stamps) >= CONTACT_RATE_LIMIT:
        cache.set(key, stamps, CONTACT_RATE_WINDOW_SEC)
        return True
    stamps.append(now)
    cache.set(key, stamps, CONTACT_RATE_WINDOW_SEC)
    return False


def _error(code, field=None, status=400):
    payload = {'status': 'error', 'code': code}
    if field:
        payload['field'] = field
    return JsonResponse(payload, status=status)


@require_POST
def contact_message_api(request):
    if _rate_limited(_client_ip(request)):
        return _error('rate_limit', status=429)

    try:
        raw = request.body.decode('utf-8') or '{}'
        data = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _error('invalid')

    if not isinstance(data, dict):
        return _error('invalid')

    # Honeypot: bots fill hidden fields; humans leave empty.
    if _as_text(data.get('website'), 200):
        return JsonResponse({'status': 'success', 'message': 'Message received.'})

    name = _as_text(data.get('name'), 120)
    email = _as_text(data.get('email'), 254)
    subject = _as_text(data.get('subject'), 200)
    message = _as_text(data.get('message'), 5000)

    if len(name) < 2:
        return _error('err_name', field='name')
    if not EMAIL_RE.match(email):
        return _error('err_email', field='email')
    if len(subject) < 3:
        return _error('err_subject', field='subject')
    if len(message) < 20:
        return _error('err_message', field='message')

    ContactMessage.objects.create(
        name=name,
        email=email,
        subject=subject,
        message=message,
    )
    return JsonResponse({
        'status': 'success',
        'code': 'ok',
    })
