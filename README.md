# Carthy — Student Well-being Platform

> A digital platform designed to support students' emotional well-being through active listening, scheduled support sessions, and accessible mental health resources.

## About Carthy

**Carthy** is a student well-being platform developed as an academic technology project focused on providing students with a safe and accessible space to seek emotional support.

The platform allows students to schedule support sessions, communicate through an in-app well-being chat, track their daily mood, and access useful resources related to emotional well-being.

Carthy also provides tools for psychologists or listeners to manage sessions and maintain confidential notes.

## Our Mission

Carthy aims to make emotional support more accessible to students by combining technology, organization, and human connection in a simple and user-friendly platform.

The project focuses on creating a space where students can:

* Find emotional support more easily.
* Schedule sessions according to their availability.
* Keep track of their well-being.
* Communicate through a dedicated support environment.
* Access educational resources about emotional health.

## Features

### User Accounts

* Student and psychologist/listener roles.
* Registration and login.
* Login using username or email.
* Password recovery.
* Persistent sessions.
* User profile with name, email, and profile picture.

### Session Management

Students can:

* Schedule support sessions.
* Select a date and available time slot.
* Choose between available modalities.
* Select a psychologist/listener.
* View their session history.
* Confirm sessions.
* Reschedule sessions.
* Cancel sessions.
* Mark completed sessions.

Psychologists/listeners can manage their availability.

### Well-being Chat

Carthy includes an in-app communication space designed for well-being support.

### Confidential Notes

Psychologists can maintain confidential notes related to support sessions.

### Daily Mood Tracking

Students can record their daily mood as part of their personal well-being tracking.

### Notifications

The platform includes in-app notifications to help users stay informed about important events and sessions.

### User Interface

Carthy includes:

* Responsive design.
* Desktop navigation.
* Mobile bottom navigation.
* Light and dark mode.
* Spanish and English interface options.
* Modern and minimalistic design.

## Technologies

### Frontend

* HTML5
* React.js
* Tailwind CSS

### Backend

* Python
* Django

### Database

* SQLite during development

### Development Tools

* Git
* GitHub
* Django Admin

## Project Structure

```text
Carthy/
│
├── bienestar/
│   ├── migrations/
│   ├── templates/
│   ├── models.py
│   ├── views.py
│   └── ...
│
├── manage.py
├── requirements.txt
├── .gitignore
└── ...
```

## Installation

### 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
```

### 2. Enter the project directory

```bash
cd Carthy
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Apply migrations

```bash
python manage.py migrate
```

### 6. Start the development server

```bash
python manage.py runserver
```

## Security

Security and privacy are important aspects of Carthy because the platform is designed around student well-being information.

Sensitive development files should not be included in the public repository, including:

* `.env`
* `db.sqlite3`
* API keys
* Passwords
* Authentication tokens
* Real user information
* Secret keys

Sensitive configuration values should be stored using environment variables rather than directly inside the source code.

> Before deploying Carthy to production, additional security measures should be implemented, including HTTPS, secure authentication configuration, database security, and proper protection of sensitive information.

## Team

Carthy was developed by a **7-member student team** as part of an academic excellence project.

The project involves areas such as:

* Project management
* UI/UX design
* Frontend development
* Backend development
* Database development
* Documentation
* Communication and presentation

## Screenshots

Screenshots of the Carthy interface can be added here to showcase the platform.

### Dashboard

*Add screenshot here.*

### Session Scheduling

*Add screenshot here.*

### Well-being Chat

*Add screenshot here.*

### User Profile

*Add screenshot here.*

## Future Improvements

Potential future improvements include:

* Expanding the well-being resources section.
* Improving the psychologist/listener interface.
* Adding more advanced mood-tracking features.
* Improving notification functionality.
* Expanding multilingual support.
* Strengthening security for production deployment.
* Integrating additional AI-powered well-being tools.

## Academic Project

Carthy was developed as an academic technology project with the goal of applying programming, web development, database management, UI/UX design, and project management skills to a real-world problem.

The project demonstrates how modern web technologies can be used to create a platform focused on student well-being.

---

**Carthy — Technology with a human purpose.**
