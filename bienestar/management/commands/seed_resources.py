from datetime import date

from django.core.management.base import BaseCommand

from bienestar.models import Resource, DailyInspiration


SAMPLE_RESOURCES = [
    {
        'title_en': 'Understanding Anxiety in Student Life',
        'title_es': 'Entender la ansiedad en la vida estudiantil',
        'short_description_en': 'Learn how anxiety shows up during exams, deadlines, and social pressure — and practical first steps to feel steadier.',
        'short_description_es': 'Aprende cómo aparece la ansiedad en exámenes, entregas y presión social, y primeros pasos prácticos para sentirte más estable.',
        'full_content_en': """Anxiety is a natural response to stress, but when it becomes constant it can affect sleep, concentration, and relationships.

## What is Anxiety
Anxiety is your body’s alarm system. In student life it often activates around evaluations, social comparison, and uncertainty about the future.

## Symptoms
Common signs include racing thoughts before exams, avoiding social situations, muscle tension, and irritability.

## Causes
Deadlines, sleep debt, caffeine overload, and perfectionism can keep the alarm switched on longer than needed.

## Tips
• Name what you feel without judgment (“I notice anxiety right now”).
• Break tasks into small, timed blocks.
• Keep a consistent sleep and meal routine during high-pressure weeks.
• Reach out to a trusted friend, counselor, or Carthy listener when the load feels heavy.

## When to Seek Help
If anxiety interferes with daily functioning for weeks, talking with a listener or professional can help you rebuild steadiness.""",
        'full_content_es': """La ansiedad es una respuesta natural al estrés, pero cuando se vuelve constante puede afectar el sueño, la concentración y las relaciones.

## Qué es la ansiedad
La ansiedad es el sistema de alarma del cuerpo. En la vida estudiantil suele activarse con evaluaciones, comparación social e incertidumbre.

## Síntomas
Pensamientos acelerados antes de exámenes, evitar situaciones sociales, tensión muscular e irritabilidad.

## Causas
Fechas límite, falta de sueño, exceso de cafeína y perfeccionismo pueden mantener la alarma encendida más de lo necesario.

## Consejos
• Nombra lo que sientes sin juicio (“Noto ansiedad ahora”).
• Divide las tareas en bloques pequeños y con tiempo.
• Mantén una rutina de sueño y comida en semanas intensas.
• Habla con alguien de confianza o un escuchador de Carthy si la carga se siente pesada.

## Cuándo pedir ayuda
Si la ansiedad interfiere con tu día a día durante semanas, una sesión de escucha o apoyo profesional puede ayudarte.""",
        'category': 'mental_health',
        'resource_type': 'article',
        'author': 'Carthy Wellness Team',
        'source_name': 'American Psychological Association',
        'source_url': 'https://www.apa.org/topics/anxiety',
        'source_author': 'APA',
        'additional_sources': 'World Health Organization|https://www.who.int/news-room/fact-sheets/detail/anxiety-disorders|WHO|2023-09-27\nHarvard Health|https://www.health.harvard.edu/mind-and-mood/anxiety-what-you-need-to-know|Harvard Health Publishing|2024-01-15',
        'reading_time': 6,
        'keywords': 'anxiety, estrés, anxiety, students, mental health, salud mental',
        'is_featured': True,
        'publication_date': date(2026, 3, 12),
    },
    {
        'title_en': '5-Minute Breathing Reset for Busy Weeks',
        'title_es': 'Reinicio de respiración de 5 minutos',
        'short_description_en': 'A short guided breathing practice you can use between classes when stress spikes.',
        'short_description_es': 'Una práctica breve de respiración para usar entre clases cuando sube el estrés.',
        'full_content_en': '## How to use this video\nSit comfortably, follow the breathing cues, and return to your day with a calmer pace.',
        'full_content_es': '## Cómo usar este video\nSiéntate con comodidad, sigue las pautas de respiración y vuelve a tu día con un ritmo más calmado.',
        'category': 'mindfulness',
        'resource_type': 'video',
        'author': 'Carthy Wellness Team',
        'source_name': 'TED-Ed',
        'source_url': 'https://ed.ted.com/',
        'reading_time': 5,
        'keywords': 'breathing, mindfulness, calm, meditation, stress, respiración',
        'youtube_url': 'https://www.youtube.com/watch?v=TXNECaIJPDI',
        'video_duration': '5:48',
        'video_channel': 'MindfulPeace',
        'is_featured': False,
        'publication_date': date(2026, 4, 2),
    },
    {
        'title_en': 'Sleep Hygiene Checklist for Students',
        'title_es': 'Lista de higiene del sueño para estudiantes',
        'short_description_en': 'A printable one-page guide to protect your sleep during midterms and finals.',
        'short_description_es': 'Una guía de una página para proteger tu sueño en parciales y finales.',
        'full_content_en': """## Why sleep matters
Sleep is a foundation of emotional regulation and academic performance.

## Checklist themes
Evening wind-down habits, caffeine timing, screen boundaries, and what to do after a restless night.""",
        'full_content_es': """## Por qué importa el sueño
El sueño es base de la regulación emocional y el rendimiento académico.

## Temas de la lista
Rutina nocturna, cafeína, pantallas y qué hacer después de una noche inquieta.""",
        'category': 'sleep',
        'resource_type': 'download',
        'author': 'Carthy Wellness Team',
        'source_name': 'CDC Sleep and Sleep Disorders',
        'source_url': 'https://www.cdc.gov/sleep/index.html',
        'additional_sources': 'National Sleep Foundation|https://www.thensf.org/',
        'reading_time': 4,
        'keywords': 'sleep, sueño, rest, hygiene, finals, habits',
        'is_featured': False,
        'publication_date': date(2026, 2, 18),
    },
    {
        'title_en': 'Managing Academic Stress Without Burning Out',
        'title_es': 'Manejar el estrés académico sin quemarte',
        'short_description_en': 'Strategies to organize workload, set boundaries, and recover energy during demanding semesters.',
        'short_description_es': 'Estrategias para organizar la carga, poner límites y recuperar energía en semestres exigentes.',
        'full_content_en': """## Start with clarity
Academic stress is common — burnout is not inevitable.

## Practical habits
• Plan tomorrow’s top three tasks the night before.
• Use short focus intervals with real breaks.
• Ask for extensions early when overload is real.
• Talk with a listener when perfectionism takes over.""",
        'full_content_es': """## Empieza con claridad
El estrés académico es común — el burnout no es inevitable.

## Hábitos prácticos
• Planifica las tres tareas top de mañana la noche anterior.
• Usa intervalos cortos de foco con descansos reales.
• Pide prórrogas a tiempo cuando la sobrecarga es real.
• Habla con un escuchador si el perfeccionismo te domina.""",
        'category': 'academic_success',
        'resource_type': 'article',
        'author': 'Carthy Wellness Team',
        'source_name': 'UNICEF',
        'source_url': 'https://www.unicef.org/mental-health',
        'additional_sources': 'American Psychological Association|https://www.apa.org/topics/stress',
        'reading_time': 7,
        'keywords': 'academic, stress, burnout, study, productividad',
        'is_featured': False,
        'publication_date': date(2026, 1, 28),
    },
    {
        'title_en': 'Building Healthier Daily Habits',
        'title_es': 'Construir hábitos diarios más saludables',
        'short_description_en': 'Small routines for movement, hydration, and emotional check-ins that fit a student schedule.',
        'short_description_es': 'Pequeñas rutinas de movimiento, hidratación y check-ins emocionales que caben en tu semana.',
        'full_content_en': """## Keep it realistic
Healthy habits work best when they are realistic.

## One anchor habit
Choose one anchor — a morning stretch, a water bottle on your desk, or a two-minute evening reflection — and attach it to something you already do.""",
        'full_content_es': """## Sé realista
Los hábitos saludables funcionan mejor cuando son realistas.

## Un hábito ancla
Elige uno — estiramiento matutino, botella de agua en el escritorio o una reflexión de dos minutos — y asócialo a algo que ya haces.""",
        'category': 'healthy_habits',
        'resource_type': 'article',
        'author': 'Carthy Wellness Team',
        'source_name': 'Harvard Health',
        'source_url': 'https://www.health.harvard.edu/',
        'reading_time': 5,
        'keywords': 'habits, hábitos, routine, wellness, movement, self-care',
        'is_featured': False,
        'publication_date': date(2026, 5, 9),
    },
    {
        'title_en': 'Communication Skills for Healthier Relationships',
        'title_es': 'Habilidades de comunicación para mejores relaciones',
        'short_description_en': 'How to listen well, set boundaries kindly, and repair misunderstandings with peers and family.',
        'short_description_es': 'Cómo escuchar bien, poner límites con amabilidad y reparar malentendidos con pares y familia.',
        'full_content_en': """## Clarity and respect
Relationships thrive on clarity and respect.

## Practice
Use “I” statements, pause before reacting, and remember that boundaries protect connection.""",
        'full_content_es': """## Claridad y respeto
Las relaciones prosperan con claridad y respeto.

## Practica
Usa mensajes en primera persona, pausa antes de reaccionar y recuerda que los límites protegen la conexión.""",
        'category': 'relationships',
        'resource_type': 'article',
        'author': 'Carthy Wellness Team',
        'source_name': 'American Psychological Association',
        'source_url': 'https://www.apa.org/topics/healthy-relationships',
        'reading_time': 6,
        'keywords': 'relationships, communication, boundaries, friends, family, relaciones',
        'is_featured': False,
        'publication_date': date(2026, 6, 1),
    },
    {
        'title_en': 'Quick Stress Relief Techniques',
        'title_es': 'Técnicas rápidas para aliviar el estrés',
        'short_description_en': 'Evidence-informed techniques you can use in under ten minutes when pressure rises.',
        'short_description_es': 'Técnicas respaldadas que puedes usar en menos de diez minutos cuando sube la presión.',
        'full_content_en': '## In this talk\nGrounding, breathing, and cognitive reframing techniques suitable for campus life.',
        'full_content_es': '## En esta charla\nTécnicas de grounding, respiración y reencuadre cognitivo útiles en el campus.',
        'category': 'stress_management',
        'resource_type': 'video',
        'author': 'Carthy Wellness Team',
        'source_name': 'World Health Organization',
        'source_url': 'https://www.who.int/news-room/questions-and-answers/item/stress',
        'reading_time': 8,
        'keywords': 'stress, relief, grounding, breathing, calm, estrés',
        'youtube_url': 'https://www.youtube.com/watch?v=5f5N6YFjvVc',
        'video_duration': '5:30',
        'video_channel': 'daringauthenticity',
        'is_featured': False,
        'publication_date': date(2026, 3, 30),
    },
]

QUOTES = [
    # Shared
    {
        'text_en': 'Your emotional wellbeing matters. We are here to listen to you.',
        'text_es': 'Tu bienestar emocional importa. Estamos aquí para escucharte.',
        'author': 'Carthy Support',
        'audience': 'ambos',
    },
    # Student — motivation, self-care, rest, organization
    {
        'text_en': 'Believe you can and you are halfway there.',
        'text_es': 'Cree que puedes y ya estás a mitad de camino.',
        'author': 'T. Roosevelt',
        'audience': 'estudiante',
    },
    {
        'text_en': 'Your mental health is a priority. Your happiness is essential.',
        'text_es': 'Tu salud mental es una prioridad. Tu felicidad es esencial.',
        'author': 'Carthy Support',
        'audience': 'estudiante',
    },
    {
        'text_en': 'One step at a time is enough of a journey.',
        'text_es': 'Un paso a la vez ya es un viaje suficiente.',
        'author': 'Ancient Wisdom',
        'audience': 'estudiante',
    },
    {
        'text_en': 'Take a deep breath. It is just a bad day, not a bad life.',
        'text_es': 'Respira profundo. Es solo un mal día, no una mala vida.',
        'author': 'Daily Inspiration',
        'audience': 'estudiante',
    },
    {
        'text_en': 'Small progress is still progress. Keep going!',
        'text_es': 'Un progreso pequeño sigue siendo progreso. ¡Sigue!',
        'author': 'Carthy Team',
        'audience': 'estudiante',
    },
    {
        'text_en': 'Rest when you are tired. Renew yourself.',
        'text_es': 'Descansa cuando estés cansado/a. Renueva tu energía.',
        'author': 'Wellbeing Guide',
        'audience': 'estudiante',
    },
    {
        'text_en': 'Organize one small task today. Clarity often starts with order.',
        'text_es': 'Organiza una tarea pequeña hoy. La claridad suele empezar con el orden.',
        'author': 'Carthy Support',
        'audience': 'estudiante',
    },
    {
        'text_en': 'Self-care is not selfish — it is how you stay present for what matters.',
        'text_es': 'El autocuidado no es egoísmo: es cómo te mantienes presente para lo que importa.',
        'author': 'Carthy Support',
        'audience': 'estudiante',
    },
    # Psych. — empathy, active listening, mental health, support, professionalism
    {
        'text_en': 'Listening is one of the most powerful ways to care.',
        'text_es': 'Escuchar es una de las formas más poderosas de cuidar.',
        'author': 'Carthy Support',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Empathy does not fix everything — it makes people feel less alone.',
        'text_es': 'La empatía no lo resuelve todo: hace que las personas se sientan menos solas.',
        'author': 'Carthy Support',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Active listening is a professional skill and a human gift.',
        'text_es': 'La escucha activa es una habilidad profesional y un regalo humano.',
        'author': 'Carthy Team',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Today you can make a difference in someone\'s life.',
        'text_es': 'Hoy puedes marcar una diferencia en la vida de alguien.',
        'author': 'Carthy Support',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Thank you for supporting the wellbeing of our students.',
        'text_es': 'Gracias por acompañar el bienestar de nuestros estudiantes.',
        'author': 'Carthy Support',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Presence, patience, and professionalism open the door to trust.',
        'text_es': 'Presencia, paciencia y profesionalismo abren la puerta a la confianza.',
        'author': 'Carthy Team',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Emotional support starts when someone feels truly heard.',
        'text_es': 'El apoyo emocional empieza cuando alguien se siente realmente escuchado.',
        'author': 'Wellbeing Guide',
        'audience': 'escuchador',
    },
    {
        'text_en': 'Protecting mental health is collective work — thank you for being part of it.',
        'text_es': 'Proteger la salud mental es un trabajo colectivo: gracias por ser parte de él.',
        'author': 'Carthy Support',
        'audience': 'escuchador',
    },
]


class Command(BaseCommand):
    help = 'Seed bilingual Wellness Hub resources and Daily Inspiration quotes.'

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in SAMPLE_RESOURCES:
            obj, was_created = Resource.objects.update_or_create(
                title_en=data['title_en'],
                defaults={**data, 'is_published': True},
            )
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'Created: {obj.title_en}'))
            else:
                updated += 1
                self.stdout.write(f'Updated: {obj.title_en}')

        q_created = 0
        q_updated = 0
        for q in QUOTES:
            obj, was_created = DailyInspiration.objects.update_or_create(
                text_en=q['text_en'],
                defaults={
                    'text_es': q.get('text_es', ''),
                    'author': q.get('author', 'Carthy Support'),
                    'audience': q.get('audience', 'ambos'),
                    'is_active': True,
                },
            )
            if was_created:
                q_created += 1
            else:
                q_updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Resources: {created} created, {updated} updated. '
            f'Quotes: {q_created} new, {q_updated} updated. '
            f'Total published resources: {Resource.objects.filter(is_published=True).count()}'
        ))
