# PenTutor – E-Learning Management System

**A full-stack, real-time e-learning platform** with role-based access, live meeting monitoring, admin dashboard, payment integration, and WebSocket-powered alerts.

Built with **Django**, **Django REST Framework**, **Channels**, **Redis**, and **Celery** — designed for **scalability**, **performance**, and **real-time user experience**.

## 🌟 Core Features

| Feature | Description |
|-------|-----------|
| **Multi-Role System** | Students, Teachers, Admins, Sub-Admins with granular permissions |
| **Real-Time Meetings** | Instant/scheduled lectures, screen sharing, recording, chat, reactions |
| **Live Inactivity Alerts** | WebSocket + Redis heartbeat system detects inactive users |
| **Google Calendar Sync** | OAuth2 integration, event sync, push notifications |
| **AI Chatbot** | Context-aware help in meetings and courses |
| **Job Board** | Students post teaching jobs; teachers apply and get reviewed |
| **Payment Integration** | Subscriptions, one-time payments, revenue analytics |
| **Automated Emails** | Progress reports, reminders, confirmations via Celery |
| **Progress Tracking** | Video/quiz completion, enrollment stats, recommendations |
| **Admin Dashboard** | User/course/payment management, support tickets, analytics |

## 🚀 Apps & Modules

| App | Purpose |
|-----|--------|
| `lms` | Core project config, ASGI/WSGI, Celery, middleware |
| `admin_dashboard` | Full admin panel with analytics & management |
| `alerts` | Real-time inactivity detection & WebSocket alerts |
| `authentication` | JWT login, email verification, role-based profiles |
| `calendersync` | Google Calendar OAuth, sync, push notifications |
| `chat` | Real-time meeting chat + AI assistant |
| `chate_box` | Entity-linked chat rooms (course, meeting, job) |
| `courses` | Course/topic/video/quiz/assignment management |
| `email_automation` | Templated emails with Celery queue |
| `individual_live_class` | 1-on-1 classes with subscriptions & rescheduling |
| `job_board` | Student job posts → teacher applications → reviews |
| `meetings` | Full-featured video conferencing (recordings via FFmpeg) |
| `notifications` | Real-time, signal-driven, bulk notifications |
| `student_dashboard` | Personalized student portal with progress & recommendations |
| `support_feedback` | Tickets, feedback, real-time admin replies |
| `teacher_dashboard` | Teacher control center: CRUD content, analytics, live classes |

## 🛠 Tech Stack

```yaml
Backend:        Django 4.x + Django REST Framework
Realtime:       Django Channels + WebSockets
Cache/Queue:    Redis
Tasks:          Celery + Celery Beat
Database:       PostgreSQL
Auth:           JWT (djangorestframework-simplejwt)
API Docs:       drf-yasg (Swagger/Redoc)
Calendar:       Google Calendar API + OAuth2
Recording:      FFmpeg
Frontend:       Ready for React/Vue (CORS enabled)
Deployment:     ASGI (Daphne) / WSGI (Gunicorn)

📡 Real-Time Features

WebSocket Alerts – Inactivity detection (>3 mins) → host notification
Live Chat – Meeting & entity-linked chat rooms
Meeting Reactions – Emoji reactions, hand-raising, muting
Push Notifications – Google Calendar changes, enrollment updates
Online Status – Redis-backed presence tracking


🔐 Security & Permissions

JWT Authentication with email verification
Role-based access (student, teacher, admin, subadmin)
Custom permissions: IsTeacher, IsStudent, etc.
Profile approval workflow (teachers/students)
Secure media handling & file upload limits
Global error middleware with JSON responses


📊 API Documentation
Live interactive docs:

Swagger UI: http://localhost:8000/swagger/
Redoc: http://localhost:8000/redoc/

All endpoints include:

JWT Bearer Auth
Request/Response examples
Filtering, pagination, search


🚦 Getting Started
Prerequisites
bashPython 3.9+
PostgreSQL
Redis
Celery
FFmpeg (for recording)
Installation
bash# Clone the repo
git clone https://github.com/yourusername/PenTutor.git
cd PenTutor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your DB, Redis, Email, Google OAuth, etc.

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Start Redis & Celery
redis-server &
celery -A lms worker -l info &
celery -A lms beat -l info &

# Run server
python manage.py runserver

🔧 Environment Variables (.env)
envDEBUG=True
SECRET_KEY=your-secret-key
DB_NAME=pentutor_db
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432

REDIS_URL=redis://localhost:6379/1

EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

JWT_SECRET=your-jwt-secret

🧪 Testing
bashpython manage.py test

Add unit tests in each app's tests.py


📈 Admin Dashboard
Access at: http://localhost:8000/admin/
Features:

User management (role changes, profile approval)
Course & enrollment tracking
Payment verification
Support tickets & feedback
Revenue analytics


🎨 Student & Teacher Dashboards

RoleURLStudent/api/student/Teacher/api/teacher/
Both return rich JSON with stats, courses, progress, and actions.

🤝 Contributing

Fork the repo
Create your feature branch:
bashgit checkout -b feature/amazing-feature

Commit your changes:
bashgit commit -m "Add amazing feature"

Push & open a Pull Request


📄 License
MIT License – Free to use, modify, and distribute.

👨‍💻 Author
Your Name
GitHub: @yourusername
Email: your.email@example.com

PenTutor – Empowering Education Through Technology

### How to Use This File

1. Save this content as `README.md` in the **root** of your GitHub repository.
2. Replace placeholder values:
   - `yourusername` → your GitHub username
   - Email, name, etc.
3. Upload to GitHub — it will render beautifully with formatting, tables, and code blocks.

Let me know if you want a **dark-themed version**, **badges**, or **GitHub Actions CI/CD integration** added!
