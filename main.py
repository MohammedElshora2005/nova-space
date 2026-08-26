import os
import secrets
import requests
import json
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from functools import wraps
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from groq import Groq

# ===== تحميل المتغيرات من ملف .env =====
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# ===== إعداد قاعدة البيانات =====
database_url = os.environ.get('DATABASE_URL')
if database_url:
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
else:
    database_url = 'sqlite:///nova.db'

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ===== إعداد رفع الصور =====
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ تجاهل إنشاء المجلد على Vercel (Read-only file system)
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except OSError:
    pass  # Vercel doesn't allow writing to filesystem

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db = SQLAlchemy(app)
CORS(app)

# ===== مفتاح API ناسا =====
NASA_API_KEY = os.environ.get('NASA_API_KEY', 'DEMO_KEY')

# ===== مفتاح Groq API =====
GROQ_API_KEY = os.environ.get('GROQ_API_KEY')

# ===== نماذج قاعدة البيانات =====

class User(db.Model):
    """مستخدمين الموقع"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    location = db.Column(db.String(100), default='')
    profile_image = db.Column(db.String(500), default='')
    favorite_planets = db.Column(db.Text, default='[]')
    favorite_missions = db.Column(db.Text, default='[]')
    favorite_asteroids = db.Column(db.Text, default='[]')
    favorite_stars = db.Column(db.Text, default='[]')
    favorite_galaxies = db.Column(db.Text, default='[]')
    favorite_blackholes = db.Column(db.Text, default='[]')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Mission(db.Model):
    """المهمات الفضائية"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    agency = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50))
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='planned')
    image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'agency': self.agency,
            'date': self.date or 'TBD',
            'description': self.description,
            'status': self.status,
            'image': self.image
        }

class Planet(db.Model):
    """الكواكب"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(50), default='Terrestrial')
    diameter = db.Column(db.Float)
    gravity = db.Column(db.Float)
    moons = db.Column(db.Integer, default=0)
    temperature = db.Column(db.Float)
    image = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'type': self.type,
            'diameter': self.diameter,
            'gravity': self.gravity,
            'moons': self.moons,
            'temperature': self.temperature,
            'image': self.image,
            'description': self.description
        }

class Asteroid(db.Model):
    """الكويكبات"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    size = db.Column(db.Float)
    hazardous = db.Column(db.Boolean, default=False)
    speed = db.Column(db.String(50))
    date = db.Column(db.String(50))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'size': self.size,
            'hazardous': self.hazardous,
            'speed': self.speed,
            'date': self.date,
            'description': self.description
        }

class Star(db.Model):
    """النجوم"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(100))
    distance = db.Column(db.String(50))
    temperature = db.Column(db.String(50))
    image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'type': self.type,
            'distance': self.distance,
            'temperature': self.temperature,
            'image': self.image
        }

class Galaxy(db.Model):
    """المجرات"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(100))
    distance = db.Column(db.String(50))
    stars = db.Column(db.String(100))
    diameter = db.Column(db.String(50))
    image = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'type': self.type,
            'distance': self.distance,
            'stars': self.stars,
            'diameter': self.diameter,
            'image': self.image
        }

class BlackHole(db.Model):
    """الثقوب السوداء"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    type = db.Column(db.String(100))
    mass = db.Column(db.String(50))
    distance = db.Column(db.String(50))
    diameter = db.Column(db.String(50))
    discovered = db.Column(db.String(20))
    image = db.Column(db.String(500))
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'type': self.type,
            'mass': self.mass,
            'distance': self.distance,
            'diameter': self.diameter,
            'discovered': self.discovered,
            'image': self.image,
            'description': self.description
        }

class Subscription(db.Model):
    """طلبات الانضمام"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    specialty = db.Column(db.String(100))
    message = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'specialty': self.specialty,
            'message': self.message,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M')
        }

class Feedback(db.Model):
    """تقييمات المستخدمين"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    rating = db.Column(db.Integer)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

class SavedImage(db.Model):
    """الصور المحفوظة من ناسا"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    title = db.Column(db.String(200))
    url = db.Column(db.String(500))
    explanation = db.Column(db.Text)
    date = db.Column(db.String(20))
    saved_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

# ===== إنشاء الجداول =====
with app.app_context():
    db.create_all()
    
    # إنشاء مشرف افتراضي - كلمة المرور من .env فقط
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD')
    
    if admin_password:
        if not User.query.filter_by(username=admin_username).first():
            admin = User(
                username=admin_username,
                email='admin@nova.com',
                is_admin=True
            )
            admin.set_password(admin_password)
            db.session.add(admin)
            db.session.commit()
            print(f'✅ Admin user created: {admin_username} / {admin_password}')
        else:
            print(f'✅ Admin user already exists: {admin_username}')
    else:
        print('⚠️ ADMIN_PASSWORD not set in .env - admin user not created')
    
    # ===== إضافة بيانات افتراضية للكواكب (مع type) =====
    if Planet.query.count() == 0:
        planets = [
            {'name': 'Mercury', 'type': 'Terrestrial', 'diameter': 4879, 'gravity': 3.7, 'moons': 0, 'temperature': 167, 'description': 'The smallest planet in our solar system'},
            {'name': 'Venus', 'type': 'Terrestrial', 'diameter': 12104, 'gravity': 8.87, 'moons': 0, 'temperature': 464, 'description': 'The hottest planet in our solar system'},
            {'name': 'Earth', 'type': 'Terrestrial', 'diameter': 12756, 'gravity': 9.8, 'moons': 1, 'temperature': 15, 'description': 'Our home planet'},
            {'name': 'Mars', 'type': 'Terrestrial', 'diameter': 6792, 'gravity': 3.71, 'moons': 2, 'temperature': -65, 'description': 'The red planet'},
            {'name': 'Jupiter', 'type': 'Gas Giant', 'diameter': 142984, 'gravity': 24.79, 'moons': 95, 'temperature': -110, 'description': 'The largest planet in our solar system'},
            {'name': 'Saturn', 'type': 'Gas Giant', 'diameter': 120536, 'gravity': 10.44, 'moons': 146, 'temperature': -140, 'description': 'The ringed planet'},
            {'name': 'Uranus', 'type': 'Ice Giant', 'diameter': 51118, 'gravity': 8.69, 'moons': 27, 'temperature': -195, 'description': 'The ice giant'},
            {'name': 'Neptune', 'type': 'Ice Giant', 'diameter': 49528, 'gravity': 11.15, 'moons': 16, 'temperature': -200, 'description': 'The windiest planet'},
        ]
        for p in planets:
            planet = Planet(**p)
            db.session.add(planet)
        db.session.commit()
        print('✅ Default planets added (with types)')

    # ===== إضافة بيانات افتراضية للكويكبات =====
    if Asteroid.query.count() == 0:
        asteroids = [
            {'name': '2024 XN1', 'size': 150, 'hazardous': True, 'speed': '30.7 km/s', 'date': '2026-12-15', 'description': 'Near-Earth asteroid passing close to Earth'},
            {'name': '2024 YR4', 'size': 80, 'hazardous': False, 'speed': '22.3 km/s', 'date': '2026-11-20', 'description': 'Safe asteroid in the main belt'},
            {'name': '2024 ZA1', 'size': 200, 'hazardous': True, 'speed': '35.1 km/s', 'date': '2026-10-05', 'description': 'Potentially hazardous asteroid'},
            {'name': '2024 WB2', 'size': 45, 'hazardous': False, 'speed': '18.9 km/s', 'date': '2026-09-12', 'description': 'Small safe asteroid'},
            {'name': '2024 VC3', 'size': 120, 'hazardous': False, 'speed': '25.4 km/s', 'date': '2026-08-28', 'description': 'Medium-sized safe asteroid'},
        ]
        for a in asteroids:
            asteroid = Asteroid(**a)
            db.session.add(asteroid)
        db.session.commit()
        print('✅ Default asteroids added')

    # ===== إضافة بيانات افتراضية للمهمات =====
    if Mission.query.count() == 0:
        missions = [
            {'name': 'Artemis II', 'agency': 'NASA', 'date': '2026-09-15', 'status': 'planned', 'description': 'First crewed mission to the Moon since Apollo 17'},
            {'name': 'Mars Sample Return', 'agency': 'NASA/ESA', 'date': '2028-03-01', 'status': 'planned', 'description': 'Bringing samples from Mars back to Earth'},
            {'name': 'Europa Clipper', 'agency': 'NASA', 'date': '2024-10-10', 'status': 'active', 'description': 'Exploring Jupiter\'s icy moon Europa'},
            {'name': 'James Webb', 'agency': 'NASA/ESA/CSA', 'date': '2021-12-25', 'status': 'active', 'description': 'Observing the universe in infrared'},
            {'name': 'Apollo 11', 'agency': 'NASA', 'date': '1969-07-20', 'status': 'completed', 'description': 'First humans to land on the Moon'},
        ]
        for m in missions:
            mission = Mission(**m)
            db.session.add(mission)
        db.session.commit()
        print('✅ Default missions added')

    # ===== إضافة بيانات افتراضية للنجوم =====
    if Star.query.count() == 0:
        stars = [
            {'name': 'Sirius', 'type': 'A-type main-sequence', 'distance': '8.6 ly', 'temperature': '9,940 K', 'image': 'https://images.unsplash.com/photo-1504333638930-c8787321eee0?w=400&h=300&fit=crop'},
            {'name': 'Betelgeuse', 'type': 'Red supergiant', 'distance': '642 ly', 'temperature': '3,500 K', 'image': 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=300&fit=crop'},
            {'name': 'Polaris', 'type': 'Cepheid variable', 'distance': '433 ly', 'temperature': '6,015 K', 'image': 'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop'},
            {'name': 'Vega', 'type': 'A-type main-sequence', 'distance': '25 ly', 'temperature': '9,602 K', 'image': 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=400&h=300&fit=crop'},
            {'name': 'Rigel', 'type': 'Blue supergiant', 'distance': '860 ly', 'temperature': '12,100 K', 'image': 'https://images.unsplash.com/photo-1506703719100-a0f3a48a2f8f?w=400&h=300&fit=crop'},
            {'name': 'Aldebaran', 'type': 'Red giant', 'distance': '65 ly', 'temperature': '4,000 K', 'image': 'https://images.unsplash.com/photo-1504333638930-c8787321eee0?w=400&h=300&fit=crop'},
            {'name': 'Antares', 'type': 'Red supergiant', 'distance': '550 ly', 'temperature': '3,500 K', 'image': 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=300&fit=crop'},
            {'name': 'Spica', 'type': 'B-type main-sequence', 'distance': '250 ly', 'temperature': '25,000 K', 'image': 'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop'},
        ]
        for s in stars:
            star = Star(**s)
            db.session.add(star)
        db.session.commit()
        print('✅ Default stars added')

    # ===== إضافة بيانات افتراضية للمجرات =====
    if Galaxy.query.count() == 0:
        galaxies = [
            {'name': 'Andromeda', 'type': 'Spiral', 'distance': '2.537 million ly', 'stars': '1 trillion', 'diameter': '220,000 ly', 'image': 'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=400&h=300&fit=crop'},
            {'name': 'Milky Way', 'type': 'Spiral', 'distance': '0 ly', 'stars': '100-400 billion', 'diameter': '100,000 ly', 'image': 'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop'},
            {'name': 'Triangulum', 'type': 'Spiral', 'distance': '3 million ly', 'stars': '40 billion', 'diameter': '60,000 ly', 'image': 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=300&fit=crop'},
            {'name': 'Sombrero', 'type': 'Spiral', 'distance': '29.3 million ly', 'stars': '100 billion', 'diameter': '49,000 ly', 'image': 'https://images.unsplash.com/photo-1504333638930-c8787321eee0?w=400&h=300&fit=crop'},
            {'name': 'Whirlpool', 'type': 'Spiral', 'distance': '23 million ly', 'stars': '100 billion', 'diameter': '60,000 ly', 'image': 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=400&h=300&fit=crop'},
            {'name': 'Black Eye', 'type': 'Spiral', 'distance': '17 million ly', 'stars': '30 billion', 'diameter': '50,000 ly', 'image': 'https://images.unsplash.com/photo-1506703719100-a0f3a48a2f8f?w=400&h=300&fit=crop'},
            {'name': 'Cigar Galaxy', 'type': 'Starburst', 'distance': '12 million ly', 'stars': '30 billion', 'diameter': '37,000 ly', 'image': 'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop'},
            {'name': 'Pinwheel', 'type': 'Spiral', 'distance': '21 million ly', 'stars': '100 billion', 'diameter': '170,000 ly', 'image': 'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=400&h=300&fit=crop'},
        ]
        for g in galaxies:
            galaxy = Galaxy(**g)
            db.session.add(galaxy)
        db.session.commit()
        print('✅ Default galaxies added')

    # ===== إضافة بيانات افتراضية للثقوب السوداء =====
    if BlackHole.query.count() == 0:
        blackholes = [
            {'name': 'Sagittarius A*', 'type': 'Supermassive', 'mass': '4.3 million M☉', 'distance': '26,000 ly', 'diameter': '44 million km', 'discovered': '1974', 'image': 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=300&fit=crop', 'description': 'The supermassive black hole at the center of the Milky Way galaxy.'},
            {'name': 'M87*', 'type': 'Supermassive', 'mass': '6.5 billion M☉', 'distance': '53.5 million ly', 'diameter': '38 billion km', 'discovered': '2019', 'image': 'https://images.unsplash.com/photo-1504333638930-c8787321eee0?w=400&h=300&fit=crop', 'description': 'The first black hole ever imaged by the Event Horizon Telescope.'},
            {'name': 'Cygnus X-1', 'type': 'Stellar', 'mass': '21 M☉', 'distance': '6,070 ly', 'diameter': '60 km', 'discovered': '1964', 'image': 'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop', 'description': 'One of the strongest X-ray sources in the sky and the first black hole candidate.'},
            {'name': 'Ton 618', 'type': 'Supermassive', 'mass': '66 billion M☉', 'distance': '10.4 billion ly', 'diameter': '390 billion km', 'discovered': '1970', 'image': 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=400&h=300&fit=crop', 'description': 'One of the most massive black holes ever discovered.'},
            {'name': 'NGC 1277', 'type': 'Supermassive', 'mass': '17 billion M☉', 'distance': '220 million ly', 'diameter': '100 billion km', 'discovered': '2012', 'image': 'https://images.unsplash.com/photo-1506703719100-a0f3a48a2f8f?w=400&h=300&fit=crop', 'description': 'A supermassive black hole with a mass 17 billion times that of the Sun.'},
            {'name': 'V404 Cygni', 'type': 'Stellar', 'mass': '9 M☉', 'distance': '7,800 ly', 'diameter': '30 km', 'discovered': '1989', 'image': 'https://images.unsplash.com/photo-1541701494587-cb58502866ab?w=400&h=300&fit=crop', 'description': 'A binary system containing a stellar-mass black hole.'},
            {'name': 'IC 1101', 'type': 'Supermassive', 'mass': '40 billion M☉', 'distance': '1.04 billion ly', 'diameter': '230 billion km', 'discovered': '1978', 'image': 'https://images.unsplash.com/photo-1462331940025-496dfbfc7564?w=400&h=300&fit=crop', 'description': 'The central black hole of one of the largest known galaxies.'},
            {'name': 'Henize 2-10', 'type': 'Intermediate', 'mass': '50,000 M☉', 'distance': '34 million ly', 'diameter': '150 km', 'discovered': '2011', 'image': 'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=400&h=300&fit=crop', 'description': 'A dwarf galaxy containing an intermediate-mass black hole.'},
        ]
        for b in blackholes:
            bh = BlackHole(**b)
            db.session.add(bh)
        db.session.commit()
        print('✅ Default black holes added')

# ===== دوال API ناسا =====

def get_apod():
    """جلب صورة اليوم من ناسا"""
    try:
        url = f'https://api.nasa.gov/planetary/apod?api_key={NASA_API_KEY}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        return None
    except:
        return None

def get_mars_photos(sol=1000, rover='curiosity'):
    """جلب صور المريخ"""
    try:
        url = f'https://api.nasa.gov/mars-photos/api/v1/rovers/{rover}/photos?sol={sol}&api_key={NASA_API_KEY}'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('photos', [])[:12]
        return []
    except:
        return []

def get_iss_location():
    """جلب موقع محطة الفضاء"""
    try:
        url = 'http://api.open-notify.org/iss-now.json'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get('iss_position', {})
        return {}
    except:
        return {}

def get_astronauts():
    """جلب عدد رواد الفضاء"""
    try:
        url = 'http://api.open-notify.org/astros.json'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                'number': data.get('number', 0),
                'people': data.get('people', [])
            }
        return {'number': 0, 'people': []}
    except:
        return {'number': 0, 'people': []}

def get_space_news():
    """جلب أخبار الفضاء"""
    try:
        url = 'https://api.spaceflightnewsapi.net/v4/articles/?limit=6'
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            articles = []
            for item in data.get('results', []):
                articles.append({
                    'id': item.get('id'),
                    'title': item.get('title', 'No Title'),
                    'summary': item.get('summary', 'No summary available'),
                    'url': item.get('url', '#'),
                    'image_url': item.get('image_url') or 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?w=400&h=200&fit=crop',
                    'published_at': item.get('published_at', '')[:10] if item.get('published_at') else ''
                })
            return articles
        return []
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

# ===== مصادقة =====

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please login first'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'message': 'Please login first'}), 401
        if not session.get('is_admin'):
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ===== Routes =====

@app.route('/')
def index():
    """الصفحة الرئيسية"""
    apod = get_apod()
    mars_photos = get_mars_photos(sol=1000)
    asteroids = Asteroid.query.limit(5).all()
    iss = get_iss_location()
    astronauts = get_astronauts()
    news = get_space_news()
    
    return render_template('index.html', 
                         apod=apod,
                         mars_photos=mars_photos[:6],
                         asteroids=asteroids[:5],
                         iss=iss,
                         astronauts=astronauts,
                         news=news)

@app.route('/missions')
def missions_page():
    """صفحة المهمات الفضائية"""
    return render_template('missions.html')

@app.route('/planets')
def planets_page():
    """صفحة استكشاف الكواكب"""
    return render_template('planets.html')

@app.route('/asteroids')
def asteroids_page():
    """صفحة الكويكبات"""
    return render_template('asteroids.html')

@app.route('/stars')
def stars_page():
    """صفحة النجوم"""
    return render_template('stars.html')

@app.route('/galaxies')
def galaxies_page():
    """صفحة المجرات"""
    return render_template('galaxies.html')

@app.route('/blackholes')
def blackholes_page():
    """صفحة الثقوب السوداء"""
    return render_template('blackholes.html')

@app.route('/profile')
def profile_page():
    """صفحة الملف الشخصي"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('profile.html')

@app.route('/chat')
def chat_page():
    """صفحة Nova AI"""
    return render_template('chat.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """تسجيل الدخول"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': '/admin' if user.is_admin else '/profile'
            })
        
        return jsonify({
            'success': False,
            'message': 'Invalid username or password'
        }), 401
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """تسجيل مستخدم جديد"""
    if request.method == 'POST':
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        location = data.get('location', '')
        
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'success': False, 'message': 'Email already registered'}), 400
        
        user = User(
            username=username,
            email=email,
            location=location
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful'}), 201
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """تسجيل الخروج"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_panel():
    """لوحة تحكم المشرفين"""
    if not session.get('is_admin'):
        return redirect(url_for('index'))
    return render_template('admin.html')

# ===== API - Upload Avatar =====
@app.route('/api/user/upload-avatar', methods=['POST'])
@login_required
def upload_avatar():
    """رفع صورة بروفايل"""
    try:
        if 'avatar' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['avatar']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'File type not allowed. Use PNG, JPG, JPEG, GIF, or WEBP'}), 400
        
        # حفظ الصورة
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"avatar_{session['user_id']}_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        # تحديث المستخدم
        user = db.session.get(User, session['user_id'])
        user.profile_image = f"/static/uploads/{filename}"
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Avatar updated successfully',
            'data': {'profile_image': user.profile_image}
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API - Update Profile =====
@app.route('/api/user/update', methods=['POST'])
@login_required
def update_profile():
    """تحديث بيانات المستخدم (الاسم، الإيميل، الموقع، كلمة المرور)"""
    try:
        data = request.get_json()
        user = db.session.get(User, session['user_id'])
        
        # تحديث الاسم
        if 'username' in data and data['username']:
            existing = User.query.filter_by(username=data['username']).first()
            if existing and existing.id != user.id:
                return jsonify({'success': False, 'message': 'Username already taken'}), 400
            user.username = data['username']
            session['username'] = user.username
        
        # تحديث الإيميل
        if 'email' in data and data['email']:
            existing = User.query.filter_by(email=data['email']).first()
            if existing and existing.id != user.id:
                return jsonify({'success': False, 'message': 'Email already registered'}), 400
            user.email = data['email']
        
        # تحديث الموقع
        if 'location' in data:
            user.location = data['location']
        
        # تحديث كلمة المرور
        if 'password' in data and data['password']:
            if len(data['password']) < 6:
                return jsonify({'success': False, 'message': 'Password must be at least 6 characters'}), 400
            user.set_password(data['password'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {
                'username': user.username,
                'email': user.email,
                'location': user.location,
                'profile_image': user.profile_image
            }
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Missions (مع فلترة SQL) =====

@app.route('/api/missions')
def get_missions():
    """جلب قائمة المهمات مع بحث وفلترة"""
    query = Mission.query
    
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    
    if search:
        query = query.filter(
            Mission.name.ilike(f'%{search}%') | 
            Mission.description.ilike(f'%{search}%')
        )
    if status:
        query = query.filter(Mission.status == status)
    
    missions = query.order_by(Mission.date.desc()).all()
    return jsonify({'success': True, 'data': [m.to_dict() for m in missions]})

@app.route('/api/missions/<int:mission_id>')
def get_mission_detail(mission_id):
    """جلب تفاصيل مهمة معينة"""
    mission = Mission.query.get_or_404(mission_id)
    return jsonify({'success': True, 'data': mission.to_dict()})

@app.route('/api/missions', methods=['POST'])
@admin_required
def create_mission():
    """إضافة مهمة جديدة (للأدمن فقط)"""
    try:
        data = request.get_json()
        
        mission = Mission(
            name=data.get('name'),
            agency=data.get('agency'),
            date=data.get('date'),
            description=data.get('description'),
            status=data.get('status', 'planned'),
            image=data.get('image')
        )
        
        db.session.add(mission)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mission added successfully', 'data': mission.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/missions/<int:mission_id>', methods=['PUT'])
@admin_required
def update_mission(mission_id):
    """تعديل مهمة (للأدمن فقط)"""
    try:
        mission = Mission.query.get_or_404(mission_id)
        data = request.get_json()
        
        if 'name' in data:
            mission.name = data['name']
        if 'agency' in data:
            mission.agency = data['agency']
        if 'date' in data:
            mission.date = data['date']
        if 'description' in data:
            mission.description = data['description']
        if 'status' in data:
            mission.status = data['status']
        if 'image' in data:
            mission.image = data['image']
        
        mission.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Mission updated successfully', 'data': mission.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/missions/<int:mission_id>', methods=['DELETE'])
@admin_required
def delete_mission(mission_id):
    """حذف مهمة (للأدمن فقط)"""
    try:
        mission = Mission.query.get_or_404(mission_id)
        db.session.delete(mission)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Mission deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Planets (مع فلترة SQL) =====

@app.route('/api/planets')
def get_planets():
    """جلب بيانات الكواكب مع بحث وفلترة حسب النوع"""
    query = Planet.query
    
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    if search:
        query = query.filter(
            Planet.name.ilike(f'%{search}%') | 
            Planet.description.ilike(f'%{search}%')
        )
    if type_filter:
        query = query.filter(Planet.type == type_filter)
    
    planets = query.order_by(Planet.name).all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in planets]})

@app.route('/api/planets/<int:planet_id>')
def get_planet_detail(planet_id):
    """جلب تفاصيل كوكب معين"""
    planet = Planet.query.get_or_404(planet_id)
    return jsonify({'success': True, 'data': planet.to_dict()})

@app.route('/api/planets', methods=['POST'])
@admin_required
def create_planet():
    """إضافة كوكب جديد (للأدمن فقط)"""
    try:
        data = request.get_json()
        
        planet = Planet(
            name=data.get('name'),
            type=data.get('type', 'Terrestrial'),
            diameter=data.get('diameter'),
            gravity=data.get('gravity'),
            moons=data.get('moons', 0),
            temperature=data.get('temperature'),
            image=data.get('image'),
            description=data.get('description')
        )
        
        db.session.add(planet)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Planet added successfully', 'data': planet.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/planets/<int:planet_id>', methods=['PUT'])
@admin_required
def update_planet(planet_id):
    """تعديل كوكب (للأدمن فقط)"""
    try:
        planet = Planet.query.get_or_404(planet_id)
        data = request.get_json()
        
        if 'name' in data:
            planet.name = data['name']
        if 'type' in data:
            planet.type = data['type']
        if 'diameter' in data:
            planet.diameter = data['diameter']
        if 'gravity' in data:
            planet.gravity = data['gravity']
        if 'moons' in data:
            planet.moons = data['moons']
        if 'temperature' in data:
            planet.temperature = data['temperature']
        if 'image' in data:
            planet.image = data['image']
        if 'description' in data:
            planet.description = data['description']
        
        planet.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Planet updated successfully', 'data': planet.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/planets/<int:planet_id>', methods=['DELETE'])
@admin_required
def delete_planet(planet_id):
    """حذف كوكب (للأدمن فقط)"""
    try:
        planet = Planet.query.get_or_404(planet_id)
        db.session.delete(planet)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Planet deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Asteroids (مع فلترة SQL) =====

@app.route('/api/asteroids')
def get_asteroids():
    """جلب بيانات الكويكبات مع بحث وفلترة"""
    query = Asteroid.query
    
    search = request.args.get('search', '')
    hazardous = request.args.get('hazardous', '')
    
    if search:
        query = query.filter(
            Asteroid.name.ilike(f'%{search}%') | 
            Asteroid.description.ilike(f'%{search}%')
        )
    if hazardous != '':
        query = query.filter(Asteroid.hazardous == (hazardous.lower() == 'true'))
    
    asteroids = query.order_by(Asteroid.date.desc()).all()
    return jsonify({'success': True, 'data': [a.to_dict() for a in asteroids]})

@app.route('/api/asteroids/<int:asteroid_id>')
def get_asteroid_detail(asteroid_id):
    """جلب تفاصيل كويكب معين"""
    asteroid = Asteroid.query.get_or_404(asteroid_id)
    return jsonify({'success': True, 'data': asteroid.to_dict()})

@app.route('/api/asteroids', methods=['POST'])
@admin_required
def create_asteroid():
    """إضافة كويكب جديد (للأدمن فقط)"""
    try:
        data = request.get_json()
        
        asteroid = Asteroid(
            name=data.get('name'),
            size=data.get('size'),
            hazardous=data.get('hazardous', False),
            speed=data.get('speed'),
            date=data.get('date'),
            description=data.get('description')
        )
        
        db.session.add(asteroid)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Asteroid added successfully', 'data': asteroid.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/asteroids/<int:asteroid_id>', methods=['PUT'])
@admin_required
def update_asteroid(asteroid_id):
    """تعديل كويكب (للأدمن فقط)"""
    try:
        asteroid = Asteroid.query.get_or_404(asteroid_id)
        data = request.get_json()
        
        if 'name' in data:
            asteroid.name = data['name']
        if 'size' in data:
            asteroid.size = data['size']
        if 'hazardous' in data:
            asteroid.hazardous = data['hazardous']
        if 'speed' in data:
            asteroid.speed = data['speed']
        if 'date' in data:
            asteroid.date = data['date']
        if 'description' in data:
            asteroid.description = data['description']
        
        asteroid.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Asteroid updated successfully', 'data': asteroid.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/asteroids/<int:asteroid_id>', methods=['DELETE'])
@admin_required
def delete_asteroid(asteroid_id):
    """حذف كويكب (للأدمن فقط)"""
    try:
        asteroid = Asteroid.query.get_or_404(asteroid_id)
        db.session.delete(asteroid)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Asteroid deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Stars (مع فلترة SQL) =====

@app.route('/api/stars')
def get_stars():
    """جلب بيانات النجوم مع بحث وفلترة"""
    query = Star.query
    
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    if search:
        query = query.filter(
            Star.name.ilike(f'%{search}%') | 
            Star.type.ilike(f'%{search}%')
        )
    if type_filter:
        query = query.filter(Star.type == type_filter)
    
    stars = query.order_by(Star.name).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in stars]})

@app.route('/api/stars/<int:star_id>')
def get_star_detail(star_id):
    """جلب تفاصيل نجم معين"""
    star = Star.query.get_or_404(star_id)
    return jsonify({'success': True, 'data': star.to_dict()})

@app.route('/api/stars', methods=['POST'])
@admin_required
def create_star():
    """إضافة نجم جديد (للأدمن فقط)"""
    try:
        data = request.get_json()
        
        star = Star(
            name=data.get('name'),
            type=data.get('type'),
            distance=data.get('distance'),
            temperature=data.get('temperature'),
            image=data.get('image')
        )
        
        db.session.add(star)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Star added successfully', 'data': star.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/stars/<int:star_id>', methods=['PUT'])
@admin_required
def update_star(star_id):
    """تعديل نجم (للأدمن فقط)"""
    try:
        star = Star.query.get_or_404(star_id)
        data = request.get_json()
        
        if 'name' in data:
            star.name = data['name']
        if 'type' in data:
            star.type = data['type']
        if 'distance' in data:
            star.distance = data['distance']
        if 'temperature' in data:
            star.temperature = data['temperature']
        if 'image' in data:
            star.image = data['image']
        
        star.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Star updated successfully', 'data': star.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/stars/<int:star_id>', methods=['DELETE'])
@admin_required
def delete_star(star_id):
    """حذف نجم (للأدمن فقط)"""
    try:
        star = Star.query.get_or_404(star_id)
        db.session.delete(star)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Star deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Galaxies (مع فلترة SQL) =====

@app.route('/api/galaxies')
def get_galaxies():
    """جلب بيانات المجرات مع بحث وفلترة"""
    query = Galaxy.query
    
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    if search:
        query = query.filter(
            Galaxy.name.ilike(f'%{search}%') | 
            Galaxy.type.ilike(f'%{search}%')
        )
    if type_filter:
        query = query.filter(Galaxy.type == type_filter)
    
    galaxies = query.order_by(Galaxy.name).all()
    return jsonify({'success': True, 'data': [g.to_dict() for g in galaxies]})

@app.route('/api/galaxies/<int:galaxy_id>')
def get_galaxy_detail(galaxy_id):
    """جلب تفاصيل مجرة معينة"""
    galaxy = Galaxy.query.get_or_404(galaxy_id)
    return jsonify({'success': True, 'data': galaxy.to_dict()})

@app.route('/api/galaxies', methods=['POST'])
@admin_required
def create_galaxy():
    """إضافة مجرة جديدة (للأدمن فقط)"""
    try:
        data = request.get_json()
        
        galaxy = Galaxy(
            name=data.get('name'),
            type=data.get('type'),
            distance=data.get('distance'),
            stars=data.get('stars'),
            diameter=data.get('diameter'),
            image=data.get('image')
        )
        
        db.session.add(galaxy)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Galaxy added successfully', 'data': galaxy.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/galaxies/<int:galaxy_id>', methods=['PUT'])
@admin_required
def update_galaxy(galaxy_id):
    """تعديل مجرة (للأدمن فقط)"""
    try:
        galaxy = Galaxy.query.get_or_404(galaxy_id)
        data = request.get_json()
        
        if 'name' in data:
            galaxy.name = data['name']
        if 'type' in data:
            galaxy.type = data['type']
        if 'distance' in data:
            galaxy.distance = data['distance']
        if 'stars' in data:
            galaxy.stars = data['stars']
        if 'diameter' in data:
            galaxy.diameter = data['diameter']
        if 'image' in data:
            galaxy.image = data['image']
        
        galaxy.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Galaxy updated successfully', 'data': galaxy.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/galaxies/<int:galaxy_id>', methods=['DELETE'])
@admin_required
def delete_galaxy(galaxy_id):
    """حذف مجرة (للأدمن فقط)"""
    try:
        galaxy = Galaxy.query.get_or_404(galaxy_id)
        db.session.delete(galaxy)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Galaxy deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Black Holes (مع فلترة SQL) =====

@app.route('/api/blackholes')
def get_blackholes():
    """جلب بيانات الثقوب السوداء مع بحث وفلترة"""
    query = BlackHole.query
    
    search = request.args.get('search', '')
    type_filter = request.args.get('type', '')
    
    if search:
        query = query.filter(
            BlackHole.name.ilike(f'%{search}%') | 
            BlackHole.description.ilike(f'%{search}%')
        )
    if type_filter:
        query = query.filter(BlackHole.type == type_filter)
    
    blackholes = query.order_by(BlackHole.name).all()
    return jsonify({'success': True, 'data': [b.to_dict() for b in blackholes]})

@app.route('/api/blackholes/<int:bh_id>')
def get_blackhole_detail(bh_id):
    """جلب تفاصيل ثقب أسود معين"""
    bh = BlackHole.query.get_or_404(bh_id)
    return jsonify({'success': True, 'data': bh.to_dict()})

@app.route('/api/blackholes', methods=['POST'])
@admin_required
def create_blackhole():
    """إضافة ثقب أسود جديد (للأدمن فقط)"""
    try:
        data = request.get_json()
        
        bh = BlackHole(
            name=data.get('name'),
            type=data.get('type'),
            mass=data.get('mass'),
            distance=data.get('distance'),
            diameter=data.get('diameter'),
            discovered=data.get('discovered'),
            image=data.get('image'),
            description=data.get('description')
        )
        
        db.session.add(bh)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Black hole added successfully', 'data': bh.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/blackholes/<int:bh_id>', methods=['PUT'])
@admin_required
def update_blackhole(bh_id):
    """تعديل ثقب أسود (للأدمن فقط)"""
    try:
        bh = BlackHole.query.get_or_404(bh_id)
        data = request.get_json()
        
        if 'name' in data:
            bh.name = data['name']
        if 'type' in data:
            bh.type = data['type']
        if 'mass' in data:
            bh.mass = data['mass']
        if 'distance' in data:
            bh.distance = data['distance']
        if 'diameter' in data:
            bh.diameter = data['diameter']
        if 'discovered' in data:
            bh.discovered = data['discovered']
        if 'image' in data:
            bh.image = data['image']
        if 'description' in data:
            bh.description = data['description']
        
        bh.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Black hole updated successfully', 'data': bh.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/blackholes/<int:bh_id>', methods=['DELETE'])
@admin_required
def delete_blackhole(bh_id):
    """حذف ثقب أسود (للأدمن فقط)"""
    try:
        bh = BlackHole.query.get_or_404(bh_id)
        db.session.delete(bh)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Black hole deleted successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

# ===== API Routes - Other =====

@app.route('/api/space-data')
def space_data():
    """جلب كل بيانات الفضاء دفعة واحدة"""
    return jsonify({
        'apod': get_apod(),
        'mars_photos': get_mars_photos(),
        'iss': get_iss_location(),
        'astronauts': get_astronauts()
    })

@app.route('/api/astro')
def get_astro_data():
    """جلب بيانات رواد الفضاء والموقع"""
    astronauts = get_astronauts()
    iss = get_iss_location()
    return jsonify({
        'success': True,
        'data': {
            'astronauts': astronauts,
            'iss': iss
        }
    })

@app.route('/api/space-news')
def get_news():
    """جلب أخبار الفضاء"""
    news = get_space_news()
    return jsonify({'success': True, 'data': news})

@app.route('/api/user/profile', methods=['GET'])
def get_profile():
    """جلب بيانات المستخدم"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    user = db.session.get(User, session['user_id'])
    return jsonify({
        'success': True,
        'data': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'location': user.location,
            'profile_image': user.profile_image,
            'favorite_planets': json.loads(user.favorite_planets or '[]'),
            'favorite_missions': json.loads(user.favorite_missions or '[]'),
            'favorite_asteroids': json.loads(user.favorite_asteroids or '[]'),
            'favorite_stars': json.loads(user.favorite_stars or '[]'),
            'favorite_galaxies': json.loads(user.favorite_galaxies or '[]'),
            'favorite_blackholes': json.loads(user.favorite_blackholes or '[]'),
            'is_admin': user.is_admin,
            'created_at': user.created_at.strftime('%Y-%m-%d')
        }
    })

@app.route('/api/user/favorites', methods=['POST'])
@login_required
def update_favorites():
    """تحديث المفضلات"""
    data = request.get_json()
    user = db.session.get(User, session['user_id'])
    
    if 'planets' in data:
        user.favorite_planets = json.dumps(data['planets'])
    if 'missions' in data:
        user.favorite_missions = json.dumps(data['missions'])
    if 'asteroids' in data:
        user.favorite_asteroids = json.dumps(data['asteroids'])
    if 'stars' in data:
        user.favorite_stars = json.dumps(data['stars'])
    if 'galaxies' in data:
        user.favorite_galaxies = json.dumps(data['galaxies'])
    if 'blackholes' in data:
        user.favorite_blackholes = json.dumps(data['blackholes'])
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Favorites updated'})

# ===== API Chat =====
@app.route('/api/chat', methods=['POST'])
def chat_with_nova():
    """Nova AI - مساعد الفضاء"""
    data = request.get_json()
    user_message = data.get('message', '').strip()
    
    if not user_message:
        return jsonify({'success': False, 'message': 'Please enter a message'}), 400
    
    system_prompt = """أنت Nova، مساعد فضائي ودود ومتحمس. أنت خبير في استكشاف الفضاء وعلم الفلك.

شخصيتك:
- ودود ومتحمس، زي مرشد فضائي شغوف
- بتتكلم بشكل طبيعي زي البشر، مش روبوت
- بتحب تشارك المعلومات المثيرة عن الفضاء

أسلوبك في الرد:
- خلي ردودك قصيرة ومباشرة (جملتين إلى 4 جمل كحد أقصى)
- لو سألك عن الفضاء، جاوب بمعلومات واضحة ومثيرة
- لو سألك عن حاجة مش فضائية، اعتذر بأدب وقول إنك متخصص في الفضاء
- دايمنًا رد بنفس لغة المستخدم (عربي، إنجليزي، إلخ)
- متذكرش القواعد في كلامك، خلي ردودك طبيعية 100%

تذكر: أنت Nova، مساعد الفضاء الودود. كن طبيعياً، متحمساً، ومفيداً! 🚀🌌"""
    
    try:
        client = Groq(api_key=GROQ_API_KEY)
        
        completion = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.8,
            max_tokens=400,
            top_p=0.9
        )
        
        reply = completion.choices[0].message.content
        return jsonify({'success': True, 'reply': reply})
        
    except Exception as e:
        print(f"Groq API error: {e}")
        fallback_replies = [
            "🚀 I'm Nova, your space exploration assistant! What would you like to know about the universe?",
            "🌌 Ask me anything about space, planets, missions, and astronomy! I'm here to help.",
            "✨ I'm Nova, your space guide! What space topic interests you today?"
        ]
        import random
        return jsonify({
            'success': True,
            'reply': random.choice(fallback_replies)
        })

@app.route('/api/subscribe', methods=['POST'])
def subscribe():
    """تسجيل طلب انضمام جديد"""
    try:
        data = request.get_json()
        
        if not data.get('name') or not data.get('email'):
            return jsonify({
                'success': False,
                'message': 'Please provide name and email'
            }), 400
        
        if '@' not in data['email'] or '.' not in data['email']:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400
        
        existing = Subscription.query.filter_by(email=data['email']).first()
        if existing:
            return jsonify({
                'success': False,
                'message': 'This email is already registered'
            }), 400
        
        subscription = Subscription(
            name=data['name'],
            email=data['email'],
            specialty=data.get('specialty', 'Not specified'),
            message=data.get('message', '')
        )
        
        db.session.add(subscription)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Application submitted successfully! We will contact you soon.',
            'data': subscription.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred',
            'error': str(e)
        }), 500

@app.route('/api/subscriptions', methods=['GET'])
@login_required
def get_subscriptions():
    """جلب كل طلبات الانضمام"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    subscriptions = Subscription.query.order_by(Subscription.created_at.desc()).all()
    return jsonify({
        'success': True,
        'data': [sub.to_dict() for sub in subscriptions]
    })

@app.route('/api/subscriptions/<int:id>', methods=['PUT'])
@login_required
def update_subscription(id):
    """تحديث حالة طلب الانضمام"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        subscription = Subscription.query.get_or_404(id)
        data = request.get_json()
        
        if 'status' in data:
            subscription.status = data['status']
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Status updated successfully',
                'data': subscription.to_dict()
            })
        
        return jsonify({
            'success': False,
            'message': 'Please specify a new status'
        }), 400
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': 'An error occurred'
        }), 500

@app.route('/api/stats', methods=['GET'])
@login_required
def get_stats():
    """جلب إحصائيات الموقع"""
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    total_missions = Mission.query.count()
    total_planets = Planet.query.count()
    total_asteroids = Asteroid.query.count()
    total_stars = Star.query.count()
    total_galaxies = Galaxy.query.count()
    total_blackholes = BlackHole.query.count()
    total_subscriptions = Subscription.query.count()
    
    return jsonify({
        'success': True,
        'data': {
            'total_missions': total_missions,
            'total_planets': total_planets,
            'total_asteroids': total_asteroids,
            'total_stars': total_stars,
            'total_galaxies': total_galaxies,
            'total_blackholes': total_blackholes,
            'total_subscriptions': total_subscriptions,
            'pending': Subscription.query.filter_by(status='pending').count(),
            'approved': Subscription.query.filter_by(status='approved').count(),
            'feedback_count': Feedback.query.count()
        }
    })

# ===== معالجة الأخطاء =====

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'message': 'Page not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'success': False, 'message': 'Internal server error'}), 500

# ===== تشغيل التطبيق =====

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # ✅ Production mode (debug=False)
    app.run(host='0.0.0.0', port=port, debug=False)
