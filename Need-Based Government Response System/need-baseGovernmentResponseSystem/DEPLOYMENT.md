# Deployment Guide

## Need-Based Government Response System
### HTML + Tailwind CSS + Python Flask Version

This guide covers deploying the application to various platforms.

---

## 📋 Pre-Deployment Checklist

Before deploying to production, complete these tasks:

### Security
- [ ] Change `app.secret_key` to a secure random string
- [ ] Add environment variables for sensitive data
- [ ] Implement proper password hashing (bcrypt/argon2)
- [ ] Add CSRF protection
- [ ] Enable HTTPS/SSL
- [ ] Add rate limiting
- [ ] Validate and sanitize all user inputs
- [ ] Implement proper session management

### Database
- [ ] Replace in-memory storage with a database
- [ ] Set up database migrations
- [ ] Add database backups
- [ ] Implement connection pooling

### Features
- [ ] Add email notifications
- [ ] Implement file upload for evidence
- [ ] Add proper logging
- [ ] Set up error monitoring
- [ ] Add analytics tracking

### Performance
- [ ] Enable caching
- [ ] Optimize database queries
- [ ] Add CDN for static files
- [ ] Enable gzip compression

---

## 🚀 Deployment Options

### Option 1: Local Server (Development)

**Best for:** Testing, development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Access at: `http://localhost:5000`

---

### Option 2: Production Server (Linux)

**Best for:** Small to medium deployments

#### Step 1: Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and pip
sudo apt install python3 python3-pip python3-venv -y

# Install PostgreSQL (recommended for production)
sudo apt install postgresql postgresql-contrib -y
```

#### Step 2: Set Up Application
```bash
# Create application directory
sudo mkdir -p /var/www/government-response
cd /var/www/government-response

# Copy your application files
# Upload via SCP, Git, or FTP

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn psycopg2-binary
```

#### Step 3: Configure Gunicorn
Create `/var/www/government-response/gunicorn_config.py`:
```python
bind = "0.0.0.0:8000"
workers = 4
worker_class = "sync"
max_requests = 1000
timeout = 30
keepalive = 2
accesslog = "/var/log/gunicorn/access.log"
errorlog = "/var/log/gunicorn/error.log"
```

#### Step 4: Create Systemd Service
Create `/etc/systemd/system/government-response.service`:
```ini
[Unit]
Description=Government Response System
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/government-response
Environment="PATH=/var/www/government-response/venv/bin"
ExecStart=/var/www/government-response/venv/bin/gunicorn -c gunicorn_config.py app:app

[Install]
WantedBy=multi-user.target
```

#### Step 5: Start Service
```bash
# Create log directory
sudo mkdir -p /var/log/gunicorn

# Enable and start service
sudo systemctl enable government-response
sudo systemctl start government-response
sudo systemctl status government-response
```

#### Step 6: Configure Nginx
Create `/etc/nginx/sites-available/government-response`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /var/www/government-response/static;
        expires 30d;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/government-response /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Step 7: SSL with Let's Encrypt
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

---

### Option 3: Heroku

**Best for:** Quick deployment, free tier available

#### Step 1: Prepare Files

Create `Procfile`:
```
web: gunicorn app:app
```

Create `runtime.txt`:
```
python-3.11.0
```

Update `requirements.txt`:
```
Flask==3.0.0
Werkzeug==3.0.1
gunicorn==21.2.0
psycopg2-binary==2.9.9
```

#### Step 2: Deploy
```bash
# Login to Heroku
heroku login

# Create app
heroku create your-app-name

# Add PostgreSQL
heroku addons:create heroku-postgresql:hobby-dev

# Deploy
git init
git add .
git commit -m "Initial commit"
git push heroku main

# Open app
heroku open
```

---

### Option 4: DigitalOcean App Platform

**Best for:** Managed deployment with auto-scaling

#### Via Web Interface:
1. Go to DigitalOcean App Platform
2. Create New App
3. Connect GitHub repository
4. Select branch
5. DigitalOcean auto-detects Flask
6. Add environment variables
7. Deploy

#### Via CLI:
```bash
# Install doctl
# See: https://docs.digitalocean.com/reference/doctl/

# Create app spec (app.yaml)
doctl apps create --spec app.yaml
```

---

### Option 5: AWS EC2

**Best for:** Full control, enterprise deployments

1. Launch EC2 instance (Ubuntu 22.04)
2. SSH into instance
3. Follow "Production Server (Linux)" steps above
4. Configure security groups (ports 80, 443)
5. Attach Elastic IP
6. Set up RDS for database
7. Use Route 53 for DNS

---

### Option 6: Docker

**Best for:** Containerized deployments

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["gunicorn", "-b", "0.0.0.0:5000", "app:app"]
```

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://user:password@db:5432/govresponse
    depends_on:
      - db
    restart: always

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=govresponse
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: always

volumes:
  postgres_data:
```

Deploy:
```bash
docker-compose up -d
```

---

## 🗄️ Database Setup

### PostgreSQL (Recommended)

#### Step 1: Install psycopg2
```bash
pip install psycopg2-binary
```

#### Step 2: Update app.py
```python
import psycopg2
from psycopg2.extras import RealDictCursor
import os

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'govresponse'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password')
    )
    return conn

# Create tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS requests (
            id VARCHAR(20) PRIMARY KEY,
            citizen_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            location JSONB,
            need_type VARCHAR(50),
            severity VARCHAR(20),
            people_affected INTEGER,
            description TEXT,
            vulnerability_group JSONB,
            special_circumstances TEXT,
            is_student BOOLEAN,
            educational_needs JSONB,
            has_evidence BOOLEAN,
            status VARCHAR(20),
            submitted_at TIMESTAMP,
            updated_at TIMESTAMP,
            verification_count INTEGER,
            priority_score INTEGER,
            estimated_response_time VARCHAR(50),
            assigned_to VARCHAR(100),
            completed_at TIMESTAMP
        );
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

# Replace requests_db list with database queries
```

### SQLite (Simple alternative)
```python
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn
```

---

## 🔐 Environment Variables

Create `.env` file:
```bash
SECRET_KEY=your-super-secret-key-here-change-this
DATABASE_URL=postgresql://user:password@localhost:5432/govresponse
FLASK_ENV=production
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
```

Load in app.py:
```python
from dotenv import load_dotenv
load_dotenv()

app.secret_key = os.getenv('SECRET_KEY')
```

---

## 📧 Email Notifications

Add Flask-Mail:
```bash
pip install Flask-Mail
```

Configure:
```python
from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
app.config['MAIL_PORT'] = os.getenv('MAIL_PORT')
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')

mail = Mail(app)

def send_status_update(email, request_id, new_status):
    msg = Message(
        f'Request {request_id} Status Update',
        sender=app.config['MAIL_USERNAME'],
        recipients=[email]
    )
    msg.body = f'Your request {request_id} is now {new_status}.'
    mail.send(msg)
```

---

## 📊 Monitoring

### Add Logging
```python
import logging
from logging.handlers import RotatingFileHandler

if not app.debug:
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)
```

### Error Tracking (Sentry)
```bash
pip install sentry-sdk[flask]
```

```python
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FlaskIntegration()]
)
```

---

## 🔒 Security Hardening

### Add HTTPS redirect
```python
from flask_talisman import Talisman

if not app.debug:
    Talisman(app, force_https=True)
```

### Add CSRF protection
```bash
pip install flask-wtf
```

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect(app)
```

### Add rate limiting
```bash
pip install Flask-Limiter
```

```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)
```

---

## 🧪 Testing Before Deployment

Run these checks:
```bash
# Check Python version
python --version

# Install dependencies
pip install -r requirements.txt

# Run tests (if you have them)
python -m pytest

# Check for security issues
pip install safety
safety check

# Run the app
python app.py
```

---

## 📈 Performance Optimization

### Enable Caching
```bash
pip install Flask-Caching
```

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/api/stats')
@cache.cached(timeout=60)
def api_get_stats():
    return jsonify(get_dashboard_stats())
```

### Optimize Database Queries
- Add indexes on frequently queried fields
- Use connection pooling
- Implement query caching

### Use CDN
- Serve Tailwind CSS from CDN (already done)
- Serve Chart.js from CDN (already done)
- Use CDN for images and static files

---

## 🆘 Troubleshooting

### App won't start
- Check Python version (3.8+)
- Verify all dependencies installed
- Check for port conflicts
- Review error logs

### Database connection fails
- Verify database credentials
- Check firewall settings
- Ensure database service is running

### Templates not loading
- Verify templates directory exists
- Check template file names
- Ensure Flask is looking in correct directory

---

## 📚 Additional Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Tailwind CSS Documentation](https://tailwindcss.com/)
- [Gunicorn Documentation](https://gunicorn.org/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## ✅ Post-Deployment Checklist

After deployment:
- [ ] Test all features
- [ ] Verify SSL certificate
- [ ] Set up automated backups
- [ ] Configure monitoring/alerts
- [ ] Test mobile responsiveness
- [ ] Check performance metrics
- [ ] Review security headers
- [ ] Set up CDN (if needed)
- [ ] Document admin procedures
- [ ] Train users

---

**Good luck with your deployment! 🚀**
