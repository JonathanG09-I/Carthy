"""
Resources module: bilingual API, public library, and detail pages.
"""
import re
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db.models import Q, Max, F
from django.utils.html import escape
from django.utils.safestring import mark_safe
from .models import Resource, DailyInspiration


CATEGORY_ORDER = [key for key, _ in Resource.CATEGORY_CHOICES]

# Preferred category order for role-personalized lists (reorder only — no new system)
STUDENT_CATEGORY_PRIORITY = {
    'mental_health': 0,
    'stress_management': 1,
    'healthy_habits': 2,
    'sleep': 3,
    'mindfulness': 4,
    'academic_success': 5,
    'relationships': 6,
}
PSYCH_CATEGORY_PRIORITY = {
    'relationships': 0,
    'mental_health': 1,
    'mindfulness': 2,
    'stress_management': 3,
    'academic_success': 4,
    'healthy_habits': 5,
    'sleep': 6,
}
STUDENT_KEYWORD_BOOST = (
    'anxiety', 'ansiedad', 'stress', 'estrés', 'estres', 'sleep', 'sueño', 'sueno',
    'habit', 'hábito', 'habito', 'motivation', 'motivación', 'motivacion', 'rest', 'descanso',
)
PSYCH_KEYWORD_BOOST = (
    'listening', 'escucha', 'empathy', 'empatía', 'empatia', 'communication', 'comunicación',
    'comunicacion', 'mental health', 'salud mental', 'support', 'apoyo', 'professional',
    'profesional', 'intervention', 'intervención', 'intervencion',
)
MESES_ES = (
    'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre',
)


def _lang(request):
    lang = (request.GET.get('lang') or '').strip().lower()
    if lang in ('en', 'es'):
        return lang
    return 'en'


def _audience(request):
    raw = (request.GET.get('audience') or request.GET.get('rol') or '').strip().lower()
    if raw in ('estudiante', 'student'):
        return 'estudiante'
    if raw in ('escuchador', 'psych', 'psychologist'):
        return 'escuchador'
    return ''


def _format_pub_date(d, lang='en'):
    if not d:
        return ''
    if lang == 'es':
        return f'{d.day} de {MESES_ES[d.month - 1]} de {d.year}'
    return d.strftime('%B %d, %Y')


def _cta_label(resource, lang):
    labels = {
        'en': {
            'article': 'Read Article →',
            'video': 'Watch Video →',
            'download': 'Download PDF →' if resource.pdf_file else 'View Guide →',
        },
        'es': {
            'article': 'Leer artículo →',
            'video': 'Ver video →',
            'download': 'Descargar PDF →' if resource.pdf_file else 'Ver guía →',
        },
    }
    return labels.get(lang, labels['en']).get(resource.resource_type, 'Open →' if lang == 'en' else 'Abrir →')


def _serialize_resource(resource, request, lang='en', detail=False):
    pdf_url = resource.pdf_file.url if resource.pdf_file else ''
    pub = _format_pub_date(resource.publication_date, lang)
    data = {
        'id': resource.id,
        'title': resource.get_title(lang),
        'title_en': resource.title_en,
        'title_es': resource.title_es,
        'short_description': resource.get_short_description(lang),
        'short_description_en': resource.short_description_en,
        'short_description_es': resource.short_description_es,
        'category': resource.category,
        'category_label': resource.get_category_label(lang),
        'resource_type': resource.resource_type,
        'resource_type_label': resource.get_type_label(lang),
        'cover_image': resource.get_cover_url(),
        'author': resource.author or ('Carthy Team' if lang == 'en' else 'Equipo Carthy'),
        'source_name': resource.source_name,
        'source_url': resource.source_url,
        'reading_time': resource.reading_time,
        'publication_date': pub,
        'publication_date_es': _format_pub_date(resource.publication_date, 'es'),
        'publication_date_iso': resource.publication_date.isoformat() if resource.publication_date else '',
        'is_featured': resource.is_featured,
        'view_count': getattr(resource, 'view_count', 0) or 0,
        'keywords': resource.keywords or '',
        'tags': [t.strip() for t in (resource.keywords or '').split(',') if t.strip()][:6],
        'detail_url': f'/resources/{resource.id}/',
        'cta_label': _cta_label(resource, lang),
    }

    if detail:
        content = resource.get_full_content(lang)
        data.update({
            'full_content': content,
            'full_content_en': resource.full_content_en,
            'full_content_es': resource.full_content_es,
            'full_content_html': render_article_html(content),
            'toc': resource.extract_toc(lang),
            'toc_en': resource.extract_toc('en'),
            'toc_es': resource.extract_toc('es'),
            'keywords': resource.keywords,
            'youtube_url': resource.youtube_url,
            'youtube_embed_id': resource.get_youtube_embed_id(),
            'video_duration': resource.video_duration,
            'video_channel': resource.video_channel,
            'pdf_url': pdf_url,
            'sources': resource.get_sources_list(),
        })

    return data


def render_article_html(content):
    """Convert plain text with ## headings into readable HTML + TOC anchors."""
    if not content:
        return ''
    lines = content.splitlines()
    html_parts = []
    paragraph = []
    heading_index = 0

    def flush_paragraph():
        nonlocal paragraph
        if paragraph:
            text = ' '.join(paragraph).strip()
            if text:
                html_parts.append(f'<p>{escape(text)}</p>')
            paragraph = []

    for raw in lines:
        line = raw.rstrip()
        if line.startswith('## '):
            flush_paragraph()
            title = line[3:].strip()
            slug = re.sub(r'[^a-zA-Z0-9áéíóúüñÁÉÍÓÚÜÑ]+', '-', title).strip('-').lower() or f'section-{heading_index+1}'
            section_id = f'section-{slug}-{heading_index}'
            heading_index += 1
            html_parts.append(f'<h2 id="{escape(section_id)}">{escape(title)}</h2>')
        elif line.startswith('• ') or line.startswith('- '):
            flush_paragraph()
            html_parts.append(f'<li>{escape(line[2:].strip())}</li>')
        elif not line.strip():
            flush_paragraph()
        else:
            paragraph.append(line.strip())

    flush_paragraph()

    # Wrap consecutive <li> into <ul>
    wrapped = []
    in_list = False
    for part in html_parts:
        if part.startswith('<li>'):
            if not in_list:
                wrapped.append('<ul>')
                in_list = True
            wrapped.append(part)
        else:
            if in_list:
                wrapped.append('</ul>')
                in_list = False
            wrapped.append(part)
    if in_list:
        wrapped.append('</ul>')

    return mark_safe(''.join(wrapped))


def lista_recursos_api(request):
    """
    Lista recursos publicados. Query params:
    - lang: en | es
    - q: search
    - category: mental_health | ...
    - type: article | video | download
    """
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    lang = _lang(request)
    qs = Resource.objects.filter(is_published=True)

    category = (request.GET.get('category') or '').strip()
    if category and category != 'all':
        qs = qs.filter(category=category)

    resource_type = (request.GET.get('type') or '').strip()
    if resource_type and resource_type != 'all':
        qs = qs.filter(resource_type=resource_type)

    q = (request.GET.get('q') or '').strip()
    if q:
        category_keys = [
            key for key, label in Resource.CATEGORY_CHOICES
            if q.lower() in label.lower()
            or q.lower() in key.lower()
            or q.lower() in Resource.CATEGORY_LABELS_ES.get(key, '').lower()
        ]
        qs = qs.filter(
            Q(title_en__icontains=q)
            | Q(title_es__icontains=q)
            | Q(short_description_en__icontains=q)
            | Q(short_description_es__icontains=q)
            | Q(full_content_en__icontains=q)
            | Q(full_content_es__icontains=q)
            | Q(keywords__icontains=q)
            | Q(author__icontains=q)
            | Q(category__in=category_keys)
        )

    featured = qs.filter(is_featured=True).first()
    if not featured:
        featured = qs.first()

    resource_list = list(qs)
    sort = (request.GET.get('sort') or '').strip().lower()
    audience = _audience(request)

    if sort == 'popular':
        resource_list.sort(key=lambda r: (-(r.view_count or 0), -(r.publication_date.toordinal() if r.publication_date else 0)))
    elif sort == 'recent':
        resource_list.sort(key=lambda r: -(r.publication_date.toordinal() if r.publication_date else 0))
    elif audience:
        priority = STUDENT_CATEGORY_PRIORITY if audience == 'estudiante' else PSYCH_CATEGORY_PRIORITY
        boosts = STUDENT_KEYWORD_BOOST if audience == 'estudiante' else PSYCH_KEYWORD_BOOST

        def _sort_key(r):
            cat_rank = priority.get(r.category, 99)
            blob = ' '.join([
                r.title_en or '', r.title_es or '',
                r.keywords or '', r.short_description_en or '', r.short_description_es or '',
            ]).lower()
            boost = 0 if any(k in blob for k in boosts) else 1
            featured_rank = 0 if r.is_featured else 1
            date_rank = -(r.publication_date.toordinal() if r.publication_date else 0)
            return (cat_rank, boost, featured_rank, date_rank)

        resource_list.sort(key=_sort_key)
        if resource_list and (not category or category == 'all'):
            featured = resource_list[0]
    elif not featured and resource_list:
        featured = resource_list[0]

    # Sections for richer library UX (same queryset, different sorts — no fake data)
    recent_qs = list(Resource.objects.filter(is_published=True).order_by('-publication_date', '-created_at')[:4])
    popular_qs = list(Resource.objects.filter(is_published=True).order_by('-view_count', '-publication_date')[:4])

    resources = [_serialize_resource(r, request, lang=lang) for r in resource_list]
    featured_data = _serialize_resource(featured, request, lang=lang) if featured else None
    recent_data = [_serialize_resource(r, request, lang=lang) for r in recent_qs]
    popular_data = [_serialize_resource(r, request, lang=lang) for r in popular_qs]

    # Only categories that currently have published content (role-preferred order)
    used = set(
        Resource.objects.filter(is_published=True)
        .values_list('category', flat=True)
        .distinct()
    )
    cat_order = list(CATEGORY_ORDER)
    if audience == 'estudiante':
        cat_order = sorted(cat_order, key=lambda k: STUDENT_CATEGORY_PRIORITY.get(k, 99))
    elif audience == 'escuchador':
        cat_order = sorted(cat_order, key=lambda k: PSYCH_CATEGORY_PRIORITY.get(k, 99))

    categories = []
    for key in cat_order:
        if key in used:
            label = (
                Resource.CATEGORY_LABELS_ES[key]
                if lang == 'es'
                else dict(Resource.CATEGORY_CHOICES)[key]
            )
            categories.append({'id': key, 'label': label})

    total_published = Resource.objects.filter(is_published=True).count()
    last_updated = (
        Resource.objects.filter(is_published=True)
        .aggregate(m=Max('updated_at'))
        .get('m')
    )

    return JsonResponse({
        'status': 'success',
        'lang': lang,
        'featured': featured_data,
        'resources': resources,
        'recent': recent_data,
        'popular': popular_data,
        'categories': categories,
        'total': len(resources),
        'total_published': total_published,
        'updated_weekly': True,
        'last_updated': last_updated.isoformat() if last_updated else '',
    })


def detalle_recurso_api(request, resource_id):
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    lang = _lang(request)
    resource = get_object_or_404(Resource, id=resource_id, is_published=True)
    Resource.objects.filter(pk=resource.pk).update(view_count=F('view_count') + 1)
    resource.refresh_from_db(fields=['view_count'])
    related = (
        Resource.objects.filter(is_published=True, category=resource.category)
        .exclude(id=resource.id)[:3]
    )

    return JsonResponse({
        'status': 'success',
        'lang': lang,
        'resource': _serialize_resource(resource, request, lang=lang, detail=True),
        'related': [_serialize_resource(r, request, lang=lang) for r in related],
    })


def recursos_publicos(request):
    """Public Resources library (no login required)."""
    return render(request, 'resources_public.html')


def recurso_detalle(request, resource_id):
    resource = get_object_or_404(Resource, id=resource_id, is_published=True)
    Resource.objects.filter(pk=resource.pk).update(view_count=F('view_count') + 1)
    resource.refresh_from_db(fields=['view_count'])
    related = list(
        Resource.objects.filter(is_published=True, category=resource.category)
        .exclude(id=resource.id)[:3]
    )
    payload_en = _serialize_resource(resource, request, lang='en', detail=True)
    payload_es = _serialize_resource(resource, request, lang='es', detail=True)
    for payload in (payload_en, payload_es):
        if 'full_content_html' in payload:
            payload['full_content_html'] = str(payload['full_content_html'])

    return render(request, 'resource_detail.html', {
        'resource': resource,
        'youtube_id': resource.get_youtube_embed_id(),
        'payload_en': payload_en,
        'payload_es': payload_es,
        'related_en': [_serialize_resource(r, request, lang='en') for r in related],
        'related_es': [_serialize_resource(r, request, lang='es') for r in related],
    })


def inspiracion_diaria_api(request):
    """Return one random active daily inspiration (bilingual), optionally role-filtered."""
    if request.method != 'GET':
        return JsonResponse({'status': 'error', 'message': 'Method not allowed.'}, status=405)

    lang = _lang(request)
    audience = _audience(request)

    qs = DailyInspiration.objects.filter(is_active=True)
    if audience in ('estudiante', 'escuchador'):
        qs = qs.filter(Q(audience=audience) | Q(audience='ambos'))

    quote = qs.order_by('?').first()
    # Fallback if role pool is empty
    if not quote:
        quote = DailyInspiration.objects.filter(is_active=True).order_by('?').first()

    if not quote:
        return JsonResponse({
            'status': 'success',
            'quote': {
                'text': 'Your emotional wellbeing matters. We are here to listen to you.' if lang == 'en'
                        else 'Tu bienestar emocional importa. Estamos aquí para escucharte.',
                'author': 'Carthy Support',
            },
        })

    return JsonResponse({
        'status': 'success',
        'quote': {
            'text': quote.get_text(lang),
            'text_en': quote.text_en,
            'text_es': quote.text_es,
            'author': quote.author or 'Carthy Support',
            'audience': getattr(quote, 'audience', 'ambos'),
        },
    })
