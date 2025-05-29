from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from functools import wraps
from datetime import datetime, timedelta
import random
import json
import logging
from sqlalchemy import desc
import click
from flask.cli import with_appcontext
import google.generativeai as genai
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ensure all loggers show INFO level messages
logging.getLogger().setLevel(logging.INFO)
for handler in logging.getLogger().handlers:
    handler.setLevel(logging.INFO)

# Setup Vercel environment if needed
try:
    from build_utils import setup_vercel_env
    setup_vercel_env()
    logger.info("Vercel environment setup completed")
except ImportError:
    logger.info("build_utils not found, skipping Vercel environment setup")
except Exception as e:
    logger.error(f"Error setting up Vercel environment: {str(e)}")

app = Flask(__name__)

# Define districts globally for use in forms, etc.
DISTRICTS = ["Gangtok", "Gyalshing", "Mangan", "Namchi", "Pakyong", "Soreng"]

BLOCKS_BY_DISTRICT = {
    "Gangtok": [
        "Duga BAC",
        "Nandok BAC",
        "Martam BAC",
        "Ranka BAC",
        "Khamdong BAC",
        "Rakdong Tintek BAC"
    ],
    "Gyalshing": [
        "Gyalshing BAC",
        "Chongrang BAC",
        "Dentam BAC",
        "Yuksom BAC",
        "Thingling-Lingchom BAC"
    ],
    "Mangan": [
        "Mangan BAC",
        "Chungthang BAC",
        "Dzongu BAC",
        "Kabi BAC",
        "Passingdong BAC"
    ],
    "Namchi": [
        "Namchi BAC",
        "Jorethang BAC",
        "Ravangla BAC",
        "Temi-Namphing BAC",
        "Yangang BAC",
        "Melli BAC"
    ],
    "Pakyong": [
        "Pakyong BAC",
        "Parakha BAC",
        "Rhenock BAC",
        "Regu BAC"
    ],
    "Soreng": [
        "Soreng BAC",
        "Baiguney BAC",
        "Chumbung-Chakung BAC",
        "Daramdin BAC",
        "Okharay BAC",
        "Timberbong-Mangaltar BAC"
    ]
} # Add more comprehensive block lists as needed

# Configure database - use environment variable if available (for Vercel deployment)
# Default to a Vercel-specific path if DATABASE_URL is not set.
database_url = os.environ.get('DATABASE_URL', 'sqlite:///instance/sgay_vercel.db')
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')  # Better to use environment variable
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'jpg', 'jpeg', 'png'}

# Initialize database and migrations
from models import db, User, OTP, Project, Beneficiary, ConstructionUpdate, Notification # Updated import
from flask_migrate import Migrate

# Initialize extensions
db.init_app(app)
migrate = Migrate(app, db)

# Import and register blueprints
from admin import admin_bp
app.register_blueprint(admin_bp)  # URL prefix is already defined in the blueprint

from beneficiary import beneficiary_bp
app.register_blueprint(beneficiary_bp, url_prefix='/beneficiary')

from auth import auth_bp
app.register_blueprint(auth_bp, url_prefix='/auth')

# Create tables (this will be handled by migrations in the future)
with app.app_context():
    db.create_all()

# Decorators for route protection
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        if not user or user.role.lower() != 'admin':  # Case-insensitive check
            flash('You need admin privileges to access this page.', 'error')
            return redirect(url_for('auth.login_page'))  # Fixed redirect
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to inject user into templates
@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            # Ensure user.role is formatted correctly for templates - standardize to proper case
            if user.role.lower() == 'admin':
                user.role = 'Admin'
            elif user.role.lower() == 'nodal officer':
                user.role = 'Nodal Officer'
            elif user.role.lower() == 'state authority':
                user.role = 'State Authority'
            elif user.role.lower() == 'central authority':
                user.role = 'Central Authority'
            return dict(current_user=user, current_year=datetime.now().year)
    return dict(current_user=None, current_year=datetime.now().year)

# Custom Jinja2 filter for formatting numbers
@app.template_filter('to_locale_string')
def to_locale_string_filter(value):
    try:
        # Attempt to convert to float for formatting, handle potential errors
        num = float(value)
        return f"{num:,.0f}" # Format with commas, no decimal places for whole numbers
    except (ValueError, TypeError):
        return value # Return original value if conversion or formatting fails

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500

# Initialize DB and seed if empty
def setup_database():
    try:
        with app.app_context():
            db.create_all()
            
            # Check if we need to seed data
            if User.query.count() == 0:
                try:
                    # Try to import and run the seed script
                    from seed_dummy_data import seed_db
                    seed_db()
                except ImportError:
                    logger.warning("seed_dummy_data.py not found. Skipping data seeding.")
                except Exception as e:
                    logger.error(f"Error seeding data: {str(e)}")
    except Exception as e:
        logger.error(f"Database setup error: {str(e)}")

# Flask CLI command for database setup
@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    try:
        logger.info("Initializing the database...")
        db.drop_all() # Optional: Drop existing tables if you want a clean slate on build
        db.create_all()
        logger.info("Database tables created.")
        
        # Seed data
        try:
            from seed_dummy_data import seed_db
            logger.info("Seeding database...")
            seed_db()
            logger.info("Database seeded successfully.")
        except ImportError:
            logger.warning("seed_dummy_data.py not found. Skipping data seeding.")
        except Exception as e:
            logger.error(f"Error seeding data: {str(e)}")
            
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
    click.echo('Initialized the database.')

app.cli.add_command(init_db_command)

# Helper functions
def get_unread_notification_count(user_id):
    """Get count of unread notifications for a user"""
    return Notification.query.filter_by(user_id=user_id, is_read=False).count()

def update_user_last_login(user_id):
    """Update user's last login timestamp"""
    user = User.query.get(user_id)
    if user:
        user.last_login = datetime.utcnow()
        db.session.commit()

def format_date(date_str):
    """Format date string to a more readable format"""
    if not date_str:
        return None
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d %b %Y')
    except ValueError:
        return date_str

# Authentication routes and helpers
def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

def store_otp(application_id, otp):
    """Store OTP in database with 5 minute expiry"""
    try:
        # Delete any existing unused OTPs for this application
        OTP.query.filter_by(
            application_id=application_id,
            is_used=False
        ).delete()
        
        # Create new OTP
        new_otp = OTP(application_id=application_id, otp_code=otp)
        db.session.add(new_otp)
        db.session.commit()
        return True
    except Exception as e:
        logger.error(f"Error storing OTP: {str(e)}")
        db.session.rollback()
        return False

def verify_otp(application_id, otp):
    """Verify OTP from database"""
    try:
        # Find valid OTP
        otp_record = OTP.query.filter_by(
            application_id=application_id,
            otp_code=otp,
            is_used=False
        ).first()
        
        if not otp_record:
            return False
            
        # Check if OTP has expired
        if datetime.utcnow() > otp_record.expires_at:
            return False
            
        # Mark OTP as used
        otp_record.is_used = True
        db.session.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error verifying OTP: {str(e)}")
        return False

@app.route('/')
def index():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user and user.role == 'Admin': # Assuming role is stored as 'Admin'
            return redirect(url_for('admin.admin_dashboard')) # Redirect to admin dashboard route

    # Get some stats for the homepage
    total_projects = Project.query.count()
    completed_projects = Project.query.filter_by(status="Completed").count()
    in_progress_projects = Project.query.filter_by(status="In Progress").count()
    total_beneficiaries = Beneficiary.query.count()
    
    # Get featured projects (most recent completed ones)
    featured_projects = Project.query.filter_by(status="Completed").order_by(desc(Project.id)).limit(3).all()
    
    return render_template('index.html', 
                          active_page='home',
                          stats={
                              'total_projects': total_projects,
                              'completed_projects': completed_projects,
                              'in_progress_projects': in_progress_projects,
                              'total_beneficiaries': total_beneficiaries
                          },
                          featured_projects=featured_projects)

@app.route('/map')
def map_view():
    total_projects = Project.query.count()
    # Get all projects, ordered by most recent first, limit to 5 for non-admin users
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None

    if user and user.role == 'admin':
        recent_projects = Project.query.order_by(desc(Project.id)).all()
        is_admin = True
    else:
        recent_projects = Project.query.order_by(desc(Project.id)).limit(5).all()
        is_admin = False

    # Testimonials dictionary
    testimonials = {
        'Tawang': {'quote': 'The construction quality is excellent, and the team was very supportive throughout the process.', 
                   'name': 'Sitti Terzin', 
                   'image': 'Name- Sitti Terzin_City Name- Tawang.jpg'},
        'Papum Pare': {'quote': 'Living in our own pucca house was a dream come true. The SGAY scheme has changed our lives.',
                       'name': 'Smti Tagru Chapa',
                       'image': '10. Name- Smti Tagru Chapa_City Name-Papum Pare.jpg'},
        'Ambikapur': {'quote': 'The house has transformed our lives. My children now have a proper space to study.',
                      'name': 'Anima Mandal',
                      'image': 'Name- Anima Mandal_City Name- Ambikapur.jpeg'},
        'Surajpur': {'quote': 'The entire process was smooth and completed within promised time.',
                     'name': 'Suresh Kumar',
                     'image': 'Name- Suresh Kumar_City Name- Suraj Pur.jpg'},
        'Birgaon': {'quote': 'Our new home has given us dignity and sense of belonging.',
                    'name': 'Kamal Narayan Verma',
                    'image': 'Name- Kamal Narayan Verma_City Name- Birgaon Raipur.jpg'},
        'Dhamtari': {'quote': 'Now we have a weather-resistant home that keeps us safe during monsoons.',
                     'name': 'Satish Dewasan',
                     'image': 'Name- Satish Dewasan_City Name- Dhamtari.jpeg'},
        'Jashpur': {'quote': 'The support from local officials was exceptional throughout.',
                    'name': 'Umesh Gupta',
                    'image': 'Name- Umesh Gupta_City Name- Jashpur.jpeg'},
        'Honnali': {'quote': 'This scheme has changed our lives completely.',
                    'name': 'HANUMANTHA H',
                    'image': 'Name-HANUMANTHA H_City-Honnali.jpeg'}
    }

    # Get district statistics
    districts = {}
    for project in Project.query.all():
        if project.district not in districts:
            districts[project.district] = {
                'total': 0,
                'completed': 0,
                'in_progress': 0,
                'allocation': 0,
                'testimonial': testimonials.get(project.district, None)  # Add testimonial if available
            }
        
        districts[project.district]['total'] += 1
        districts[project.district]['allocation'] += project.allocation
        if project.status == 'Completed':
            districts[project.district]['completed'] += 1
        elif project.status == 'In Progress':
            districts[project.district]['in_progress'] += 1    # Convert projects to dictionary format for JSON serialization
    projects_dict = [project.to_dict() for project in recent_projects]
    return render_template('map.html', 
                       active_page='map', 
                       recent_projects=projects_dict,
                       total_projects=total_projects,
                       districts=districts,
                       testimonials=testimonials,
                       is_admin=is_admin)

@app.route('/progress')
def progress():
    # Get project statistics (consistent with index page)
    total_projects = Project.query.count()
    completed_projects_count = Project.query.filter_by(status="Completed").count() # Renamed for clarity
    in_progress_projects = Project.query.filter_by(status="In Progress").count()
    pending_projects = Project.query.filter_by(status="Pending").count() # This is specific to progress page
    total_beneficiaries_count = Beneficiary.query.count() # Added for consistency if needed by template

    # Get district-wise statistics
    # districts_list = ["East Sikkim", "West Sikkim", "North Sikkim", "South Sikkim"] # Using dynamic list from Project data
    all_project_districts = db.session.query(Project.district).distinct().all()
    districts_list = [d[0] for d in all_project_districts if d[0]] # Get unique district names from projects

    district_stats = {}
    
    for district_name in districts_list:
        district_total_projects = Project.query.filter_by(district=district_name).count()
        district_completed_projects = Project.query.filter_by(district=district_name, status="Completed").count()
        district_beneficiaries = Beneficiary.query.filter_by(district=district_name).count()
        
        completion_rate = (district_completed_projects / district_total_projects * 100) if district_total_projects > 0 else 0
        
        district_stats[district_name] = {
            'total_projects': district_total_projects,
            'completed_projects': district_completed_projects,
            'beneficiaries': district_beneficiaries,
            'completion_rate': round(completion_rate, 1)
        }
    
    # Get recent projects
    recent_projects_list = Project.query.order_by(desc(Project.id)).limit(5).all()
    
    # Get recent construction updates
    recent_updates = ConstructionUpdate.query.order_by(desc(ConstructionUpdate.update_date)).limit(5).all()
    
    return render_template('progress.html', 
                          active_page='progress',
                          stats={
                              'total_projects': total_projects,
                              'completed_projects': completed_projects_count,
                              'in_progress_projects': in_progress_projects,
                              'pending_projects': pending_projects, # Specific to progress page
                              'total_beneficiaries': total_beneficiaries_count, # Added for consistency
                              'completion_rate': round((completed_projects_count / total_projects * 100), 1) if total_projects > 0 else 0
                          },
                          district_stats=district_stats,
                          recent_projects=recent_projects_list,
                          recent_updates=recent_updates)

@app.route('/beneficiaries')
def beneficiaries_page():
    # Get all completed projects with their beneficiaries
    completed_projects_list = Project.query.filter_by(status="Completed").order_by(desc(Project.id)).all()
    
    # Get statistics (consistent with index page)
    total_projects = Project.query.count()
    completed_projects_count = Project.query.filter_by(status="Completed").count() # Renamed to avoid conflict
    in_progress_projects = Project.query.filter_by(status="In Progress").count()
    total_beneficiaries_count = Beneficiary.query.count() # Renamed to avoid conflict
    total_districts = len(set([p.district for p in Project.query.all()]))


    # Testimonials by district for beneficiary stories
    beneficiary_testimonials = {
        'Tawang': 'The construction quality is excellent, and the team was very supportive throughout the process.',
        'Papum Pare': 'Living in our own pucca house was a dream come true. The SGAY scheme has changed our lives.',
        'Ambikapur': 'The house has transformed our lives. My children now have a proper space to study.',
        'Surajpur': 'The entire process was smooth and completed within promised time.',
        'Birgaon': 'Our new home has given us dignity and sense of belonging.',
        'Dhamtari': 'Now we have a weather-resistant home that keeps us safe during monsoons.',
        'Jashpur': 'The support from local officials was exceptional throughout.',
        'Honnali': 'This scheme has changed our lives completely.'
    }
    
    # Mapping of district names to image filenames
    beneficiary_images = {
        'Tawang': 'Name- Sitti Terzin_City Name- Tawang.jpg',
        'Papum Pare': '10. Name- Smti Tagru Chapa_City Name-Papum Pare.jpg',
        'Ambikapur': 'Name- Anima Mandal_City Name- Ambikapur.jpeg',
        'Surajpur': 'Name- Suresh Kumar_City Name- Suraj Pur.jpg',
        'Birgaon': 'Name- Kamal Narayan Verma_City Name- Birgaon Raipur.jpg',
        'Dhamtari': 'Name- Satish Dewasan_City Name- Dhamtari.jpeg',
        'Jashpur': 'Name- Umesh Gupta_City Name- Jashpur.jpeg',
        'Honnali': 'Name-HANUMANTHA H_City-Honnali.jpeg'
    }
    
    # Featured testimonials with real beneficiary data
    testimonials = [
        {
            'name': 'Sitti Terzin',
            'location': 'Tawang',
            'image': 'Name- Sitti Terzin_City Name- Tawang.jpg',
            'quote': 'The construction quality is excellent, and the team was very supportive throughout the process. Now we have a safe and comfortable home.',
            'rating': 5
        },
        {
            'name': 'Smti Tagru Chapa',
            'location': 'Papum Pare',
            'image': '10. Name- Smti Tagru Chapa_City Name-Papum Pare.jpg',
            'quote': 'Living in our own pucca house was a dream come true. The SGAY scheme has changed our lives for the better.',
            'rating': 5
        },
        {
            'name': 'Anima Mandal',
            'location': 'Ambikapur',
            'image': 'Name- Anima Mandal_City Name- Ambikapur.jpeg',
            'quote': 'The process was smooth and transparent. We are grateful for this initiative that helped us build our own home.',
            'rating': 5
        },
        {
            'name': 'Suresh Kumar',
            'location': 'Surajpur',
            'image': 'Name- Suresh Kumar_City Name- Suraj Pur.jpg',
            'quote': 'The support from the government and the quality of construction exceeded our expectations.',
            'rating': 5
        },
        {
            'name': 'Kamal Narayan Verma',
            'location': 'Birgaon Raipur',
            'image': 'Name- Kamal Narayan Verma_City Name- Birgaon Raipur.jpg',
            'quote': 'We are proud homeowners now. The house is well-built and perfect for our family needs.',
            'rating': 5
        },
        {
            'name': 'Satish Dewasan',
            'location': 'Dhamtari',
            'image': 'Name- Satish Dewasan_City Name- Dhamtari.jpeg',
            'quote': 'The SGAY scheme has given us not just a house, but a foundation for a better future.',
            'rating': 5
        }
    ]
    
    # Featured testimonial for the bottom section
    featured_testimonial = {
        'image': testimonials[0]['image'],
        'quote': testimonials[0]['quote']
    }
    
    return render_template('beneficiary.html', 
                       active_page='beneficiaries',
                       completed_projects=completed_projects_list, # Use the list variable
                       total_houses=completed_projects_count, # Consistent with index
                       total_beneficiaries=total_beneficiaries_count, # Consistent with index
                       total_districts=total_districts,
                       testimonials=testimonials,
                       beneficiary_testimonials=beneficiary_testimonials,
                       beneficiary_images=beneficiary_images,
                       featured_testimonial=featured_testimonial,
                       # Stats for the "Impact Statistics" section, ensure they are consistent or calculated as needed
                       avg_completion_time="5.2 months", # This seems hardcoded, might need dynamic calculation
                       satisfaction_rate=95, # This seems hardcoded, might need dynamic calculation
                       districts_covered=total_districts,
                       # Pass the main stats consistent with index.html for the top section
                       # The template 'beneficiary.html' uses {{ total_houses }}, {{ total_beneficiaries }}, {{ total_districts }}
                       # We are already passing these correctly.
                       # For the "Impact Statistics" section, it uses {{ total_beneficiaries }}, {{ avg_completion_time }}, {{ satisfaction_rate }}%, {{ districts_covered }}
                       # We've updated total_beneficiaries and districts_covered for consistency.
                       # avg_completion_time and satisfaction_rate might need to be made dynamic if they aren't meant to be hardcoded.
                       # For now, I'm ensuring the main stats passed for the top section are the same as index.
                       # The 'Impact Statistics' section will use the already passed values.
                       # The original request was about: "total project complete and houses build etc should be same as index.html"
                       # 'total_houses' in beneficiary.html maps to 'completed_projects_count' from the logic.
                       # 'total_beneficiaries' maps to 'total_beneficiaries_count'.
                       # 'total_districts' is calculated consistently.
                       # The variable 'total_projects' from index.html is not directly used by name in beneficiary.html's stat display from what I saw earlier.
                       # However, to make all index.html stats available if needed, let's pass them.
                       stat_total_projects = total_projects,
                       stat_in_progress_projects = in_progress_projects
                       )

@app.route('/apply')
def apply_page():
    return render_template('apply.html', 
                           active_page='apply', 
                           districts=DISTRICTS, 
                           blocks_by_district=BLOCKS_BY_DISTRICT)

@app.route('/login')
def login_page():
    if session.get('user_id'):
        return redirect(url_for('profile'))
    return render_template('login.html', active_page='login')

@app.route('/register')
def register_page():
    if session.get('user_id'):
        return redirect(url_for('profile'))
    return render_template('register.html', active_page='register')

@app.route('/eligibility')
def eligibility_page():
    return render_template('eligibility.html', active_page='eligibility')

@app.route('/about')
def about_page():
    return render_template('about.html', active_page='about')

@app.route('/contact')
def contact_page():
    return render_template('contact.html', active_page='contact')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_progress():
    users = User.query.all()
    beneficiaries = Beneficiary.query.all()
    projects = Project.query.all()
    
    # Get some admin stats
    stats = {
        'total_users': User.query.count(),
        'total_beneficiaries': Beneficiary.query.count(),
        'total_projects': Project.query.count(),
        'pending_applications': Beneficiary.query.filter_by(status="Pending").count()
    }
    
    return render_template('admin_layout.html', 
                          users=users, 
                          beneficiaries=beneficiaries, 
                          projects=projects, 
                          stats=stats,
                          active_page='admin')

@app.route('/profile')
@login_required
def profile():
    user = User.query.get(session['user_id'])
    
    # If role is beneficiary, redirect to the beneficiary profile page
    if user.role.lower() == 'beneficiary':
        return redirect(url_for('beneficiary.profile'))
    
    # For other roles, handle accordingly
    # Get beneficiaries associated with this user
    beneficiaries = Beneficiary.query.filter_by(user_id=user.id).all()
    
    # Get notifications for this user
    notifications = Notification.query.filter_by(user_id=user.id).order_by(Notification.created_at.desc()).all()
    unread_count = get_unread_notification_count(user.id)
    
    # Redirect to admin dashboard for admin users
    if user.role.lower() in ['admin', 'nodal officer', 'state authority', 'central authority']:
        return redirect(url_for('admin.admin_dashboard'))
    
    # For any other case or fallback, redirect to home
    return redirect(url_for('index'))

@app.route('/project/<project_id>')
def project_detail(project_id):
    project = Project.query.filter_by(project_id=project_id).first_or_404()
    updates = ConstructionUpdate.query.filter_by(project_id=project_id).order_by(ConstructionUpdate.update_date.desc()).all()
    return render_template('project_detail.html', 
                          project=project, 
                          updates=updates, 
                          active_page='projects')

@app.route('/beneficiary/<beneficiary_id>')
def beneficiary_detail(beneficiary_id):
    beneficiary = Beneficiary.query.filter_by(beneficiary_id=beneficiary_id).first_or_404()
    projects = Project.query.filter_by(beneficiary_id=beneficiary_id).all()
    return render_template('beneficiary_detail.html', 
                          beneficiary=beneficiary, 
                          projects=projects, 
                          active_page='beneficiaries')

@app.route('/dashboard')
@login_required
def dashboard():
    return redirect(url_for('progress'))

# API Endpoints
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    login_type = data.get('type', 'standard')  # 'admin', 'beneficiary', or 'standard' (default)
    
    if login_type == 'beneficiary':
        # Beneficiary login via OTP is handled separately in auth/routes.py
        return jsonify({
            'success': False,
            'message': 'For beneficiary login, use the OTP login option.',
            'redirect': url_for('auth.login_page')
        })
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({
            'success': False,
            'message': 'Username and password are required.'
        }), 400
    
    # Find user
    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        # Update login attempts for security tracking
        if user:
            user.login_attempts = (user.login_attempts or 0) + 1
            user.last_failed_login = datetime.utcnow()
            db.session.commit()
            
        return jsonify({
            'success': False,
            'message': 'Invalid username or password.'
        }), 401
    
    # Check if the login type matches the user type
    if login_type == 'admin' and user.role.lower() not in ['admin', 'nodal officer', 'state authority', 'central authority']:
        return jsonify({
            'success': False,
            'message': 'You do not have admin privileges.'
        }), 403
    
    # Successful login
    session['user_id'] = user.id
    session['user_role'] = user.role
    session['last_activity'] = datetime.utcnow().timestamp()
    
    # Update user statistics
    user.last_login = datetime.utcnow()
    user.login_attempts = 0  # Reset failed attempts on successful login
    db.session.commit()
    
    # Determine redirect URL based on user role
    redirect_url = url_for('index')  # Default to home
    
    if user.role.lower() in ['admin', 'nodal officer', 'state authority', 'central authority']:
        redirect_url = url_for('admin.admin_dashboard')
    elif user.role.lower() == 'beneficiary':
        redirect_url = url_for('beneficiary.dashboard')
    
    return jsonify({
        'success': True,
        'message': 'Login successful.',
        'redirect': redirect_url,
        'user': {
            'name': user.full_name,
            'role': user.role
        }
    })

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    full_name = data.get('full_name')
    email = data.get('email')
    phone = data.get('phone')
    scheme = data.get('scheme', 'pmay')
    use_dummy_data = data.get('use_dummy_data', False)
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required.'}), 400
    
    try:
        if User.query.filter_by(username=username).first():
            return jsonify({'success': False, 'message': 'Username already exists.'}), 400
        
        user = User(
            username=username, 
            password_hash=generate_password_hash(password),
            full_name=full_name,
            email=email,
            phone=phone,
            preferred_scheme=scheme,
            created_at=datetime.utcnow()
        )
        db.session.add(user)
        db.session.commit()
        
        # Log the user in
        session['user_id'] = user.id
        update_user_last_login(user.id)
        
        # Check if we have a temporary application ID to link to this new user
        temp_application_id = session.pop('temp_application_id', None)
        if temp_application_id:
            # Find the application and link it to this user
            beneficiary = Beneficiary.query.filter_by(beneficiary_id=temp_application_id).first()
            if beneficiary and not beneficiary.user_id:
                beneficiary.user_id = user.id
                db.session.commit()
                flash(f'Your application (ID: {temp_application_id}) has been linked to your account.', 'success')
                return jsonify({'success': True, 'message': 'Registration successful. Your application has been linked to your account.', 'redirect': url_for('beneficiary.application_status')})
        
        # If using dummy data, create a sample beneficiary
        if use_dummy_data:
            district = random.choice(["East Sikkim", "West Sikkim", "North Sikkim", "South Sikkim"])
            village = random.choice(["Gangtok", "Pakyong", "Rangpo", "Gyalshing", "Soreng", "Mangan", "Namchi"])
            
            new_id = f"PMAY-{1000 + Beneficiary.query.count() + 1}"
            
            dummy_beneficiary = Beneficiary(
                beneficiary_id=new_id,
                name=full_name or 'Test User',
                district=district,
                village=village,
                status='Pending',
                progress=0,
                contactNumber=phone or '9876543210',
                address=f"Near Market, {village}, {district}",
                applicationDate=datetime.now().strftime('%Y-%m-%d'),
                annual_income=240000,
                family_members=4,
                aadhar_number="1234-5678-9012",
                occupation="Self-employed",
                housing_status="Kutcha House",
                user_id=user.id,
                scheme=scheme,
                gender='Male',
                category='General',
                bank_name='State Bank of India',
                account_number='1234567890',
                ifsc_code='SBIN0001234',
                land_ownership='Own Land',
                property_area=1200,
                pmay_component='BLC'
            )
            db.session.add(dummy_beneficiary)
            
            # Create a notification for the user
            notification = Notification(
                user_id=user.id,
                title="Dummy Application Created",
                message=f"A dummy housing application (ID: {new_id}) has been created for testing purposes.",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(notification)
            db.session.commit()
        
        return jsonify({'success': True, 'message': 'Registration successful.', 'redirect': url_for('profile')})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred during registration.'}), 500

@app.route('/api/beneficiaries', methods=['GET', 'POST'])
def api_beneficiaries():
    if request.method == 'GET':
        try:
            id_ = request.args.get('id')
            district = request.args.get('district')
            status = request.args.get('status')
            search = request.args.get('search')
            scheme = request.args.get('scheme')
            query = Beneficiary.query
            
            if id_:
                query = query.filter_by(beneficiary_id=id_)
            if district:
                query = query.filter(Beneficiary.district.ilike(district))
            if status:
                query = query.filter(Beneficiary.status.ilike(status))
            if scheme:
                query = query.filter(Beneficiary.scheme == scheme)
            if search:
                search = f"%{search}%"
                query = query.filter(
                    (Beneficiary.beneficiary_id.ilike(search)) |
                    (Beneficiary.name.ilike(search)) |
                    (Beneficiary.village.ilike(search))
                )
                
            beneficiaries = query.all()
            return jsonify([
                {
                    'id': b.beneficiary_id,
                    'name': b.name,
                    'district': b.district,
                    'village': b.village,
                    'status': b.status,
                    'progress': b.progress,
                    'contactNumber': b.contactNumber,
                    'address': b.address,
                    'applicationDate': format_date(b.applicationDate) if b.applicationDate else (b.created_at.strftime('%d %b %Y') if b.created_at else None),
                    'approvalDate': format_date(b.approvalDate),
                    'photo_url': b.photo_url,
                    'annual_income': b.annual_income,
                    'family_members': b.family_members,
                    'scheme': b.scheme or 'sgay',
                    'gender': b.gender,
                    'category': b.category,
                    'sc_certificate_filename': b.sc_certificate_filename,
                    'bank_name': b.bank_name,
                    'account_number': b.account_number,
                    'ifsc_code': b.ifsc_code,
                    'land_ownership': b.land_ownership,
                    'property_area': b.property_area,
                    'pmay_component': b.pmay_component,
                    'aadhar_number': b.aadhar_number, # Added for completeness
                    'voter_id': b.voter_id, # Added for completeness
                    'ration_card_number': b.ration_card_number, # Added for completeness
                    'income_certificate_filename': b.income_certificate_filename, # Added for completeness
                    'additional_comments': b.additional_comments # Added for completeness
                } for b in beneficiaries
            ])
        except Exception as e:
            logger.error(f"Error fetching beneficiaries: {str(e)}")
            return jsonify({'error': 'An error occurred while fetching beneficiaries.'}), 500
            
    elif request.method == 'POST':
        user_id = session.get('user_id')
        logger.info(f"****POST REQUEST RECEIVED: Application submission attempt. User ID from session: {user_id}")
        
        try:
            data = request.form.to_dict()
            logger.info(f"****Received form data with {len(data)} fields. Keys: {list(data.keys())}")
            
            income_certificate_file = request.files.get('income_certificate')
            applicant_photo_file = request.files.get('applicant_photo')
            sc_certificate_file = request.files.get('sc_certificate') # Get SC certificate file

            # Validate required fields for the new simplified form
            required_fields = ['name', 'district', 'village', 'address', 'aadhar_number', 'annual_income', 'family_members', 'housing_status']
            missing_fields = [field for field in required_fields if not data.get(field)]
            if missing_fields:
                logger.warning(f"****Missing required fields: {', '.join(missing_fields)}")
                return jsonify({'error': f"Missing required fields: {', '.join(missing_fields)}"}), 400

            # SERVER-SIDE GENERATION OF UNIQUE ID - Ignore any client-provided refId
            logger.info(f"****STARTING SERVER-SIDE ID GENERATION")
            
            # If client provided refId, log it but ignore it
            if 'refId' in data:
                logger.info(f"****Client provided refId: {data.get('refId')} - This will be IGNORED")
                
            # Generate a guaranteed unique ID using the current timestamp and a UUID
            timestamp_part = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            random_part = str(uuid.uuid4()).replace('-', '')[:8]
            
            # Format: SGAY-20250524142245-a1b2c3d4
            server_generated_id = f"SGAY-{timestamp_part}-{random_part}"
            
            logger.info(f"****Generated server-side ID: {server_generated_id}")
            
            # Debug: Check if ID already exists
            existing_check = Beneficiary.query.filter_by(beneficiary_id=server_generated_id).first()
            if existing_check:
                logger.critical(f"****CRITICAL ERROR: Generated ID {server_generated_id} already exists!!")
            else:
                logger.info(f"****Confirmed: Generated ID {server_generated_id} is unique")
            
            # Create new beneficiary - NO User account created at this stage
            new_beneficiary = Beneficiary(
                beneficiary_id=server_generated_id,  # Use our server-generated ID
                name=data.get('name'),
                district=data.get('district'),
                village=data.get('village'),
                address=data.get('address'),
                aadhar_number=data.get('aadhar_number'),
                annual_income=data.get('annual_income'),
                family_members=data.get('family_members'),
                housing_status=data.get('housing_status'),
                applicationDate=datetime.utcnow().strftime('%Y-%m-%d'),
                status='Applied',  # New initial status
                progress=5,  # Initial low progress
                # user_id will be NULL until admin approves and creates an account
                scheme=data.get('scheme', 'sgay'), 
                created_at=datetime.utcnow()
                # Other fields like gender, category, bank details, etc., will be collected later
            )

            db.session.add(new_beneficiary)
            db.session.commit()
            logger.info(f"New application {new_beneficiary.beneficiary_id} created successfully (no user account yet).")
            
            return jsonify({
                'success': True,
                'refId': new_beneficiary.beneficiary_id, 
                'name': new_beneficiary.name,
                'message': 'Application submitted successfully! Your Application ID is shown above.'
            }), 201
            
        except Exception as e:
            db.session.rollback()
            error_message = str(e)
            logger.error(f"Error creating beneficiary: {error_message}", exc_info=True) # Add exc_info for traceback
            return jsonify({
                'error': 'An error occurred while submitting your application.',
                'details': error_message if app.debug else "An internal error occurred."
            }), 500

@app.route('/api/projects', methods=['GET'])
def api_projects():
    try:
        projects = Project.query.all()
        return jsonify([
            {
                'id': p.project_id,
                'beneficiaryName': p.beneficiaryName,
                'location': p.location,
                'district': p.district,
                'status': p.status,
                'allocation': p.allocation,
                'completionPercentage': p.completionPercentage,
                'startDate': p.startDate,
                'imageUrl': p.imageUrl,
                'latitude': p.latitude,
                'longitude': p.longitude,
                'description': p.description,
                'end_date': p.end_date,
                'contractor': p.contractor,
                'beneficiary_id': p.beneficiary_id
            } for p in projects
        ])
    except Exception as e:
        logger.error(f"Error fetching projects: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching projects.'}), 500

@app.route('/api/construction-updates', methods=['GET', 'POST', 'PUT'])
def api_construction_updates():
    if request.method == 'GET':
        try:
            beneficiaryId = request.args.get('beneficiaryId')
            project_id = request.args.get('project_id')
            district = request.args.get('district')
            query = ConstructionUpdate.query
            
            if beneficiaryId:
                query = query.filter_by(beneficiaryId=beneficiaryId)
            if project_id:
                query = query.filter_by(project_id=project_id)
            if district:
                query = query.filter_by(district=district)
                
            updates = query.order_by(ConstructionUpdate.update_date.desc()).all()
            return jsonify([
                {
                    'id': u.id,
                    'beneficiaryId': u.beneficiaryId,
                    'district': u.district,
                    'location': u.location,
                    'constructionStage': u.constructionStage,
                    'completionPercentage': u.completionPercentage,
                    'notes': u.notes,
                    'photos': u.photos,
                    'timestamp': u.timestamp,
                    'update_date': u.update_date.strftime('%Y-%m-%d'),
                    'inspector': u.inspector,
                    'project_id': u.project_id
                } for u in updates
            ])
        except Exception as e:
            logger.error(f"Error fetching construction updates: {str(e)}")
            return jsonify({'error': 'An error occurred while fetching construction updates.'}), 500
            
    elif request.method == 'POST':
        # Only admin can add construction updates
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
            
        try:
            data = request.get_json()
            if not data.get('beneficiaryId') or not data.get('district') or not data.get('constructionStage'):
                return jsonify({'error': 'Missing required fields'}), 400
                
            new_update = ConstructionUpdate(
                beneficiaryId=data['beneficiaryId'],
                district=data['district'],
                location=data.get('location', ''),
                constructionStage=data['constructionStage'],
                completionPercentage=data.get('completionPercentage', 0),
                notes=data.get('notes'),
                photos=data.get('photos'),
                timestamp=int(datetime.utcnow().timestamp()),
                update_date=datetime.utcnow(),
                inspector=data.get('inspector'),
                project_id=data.get('project_id'),
                created_at=datetime.utcnow()
            )
            db.session.add(new_update)
            
            # Update the project completion percentage
            if data.get('project_id'):
                project = Project.query.filter_by(project_id=data['project_id']).first()
                if project:
                    project.completionPercentage = data.get('completionPercentage', project.completionPercentage)
                    if data['constructionStage'] == 'Completed':
                        project.status = 'Completed'
                        project.end_date = datetime.utcnow().strftime('%Y-%m-%d')
                    
                    # Update the beneficiary progress as well
                    beneficiary = Beneficiary.query.filter_by(beneficiary_id=data['beneficiaryId']).first()
                    if beneficiary:
                        beneficiary.progress = data.get('completionPercentage', beneficiary.progress)
                        if data['constructionStage'] == 'Completed':
                            beneficiary.status = 'Completed'
                        
                        # Create a notification for the beneficiary
                        if beneficiary.user_id:
                            notification = Notification(
                                user_id=beneficiary.user_id,
                                title="Construction Update",
                                message=f"Your house construction is now {data.get('completionPercentage')}% complete. Stage: {data['constructionStage']}",
                                is_read=False,
                                created_at=datetime.utcnow()
                            )
                            db.session.add(notification)
            
            db.session.commit()
            return jsonify({'id': new_update.id, 'message': 'Update added successfully'}), 201
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating construction update: {str(e)}")
            return jsonify({'error': 'An error occurred while adding the update.'}), 500
            
    elif request.method == 'PUT':
        # Only admin can update construction updates
        user_id = session.get('user_id')
        user = User.query.get(user_id) if user_id else None
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
            
        try:
            data = request.get_json()
            if not data.get('id'):
                return jsonify({'error': 'Missing update ID'}), 400
                
            update = ConstructionUpdate.query.get(data['id'])
            if not update:
                return jsonify({'error': 'Update not found'}), 404
                
            for key in ['beneficiaryId', 'district', 'location', 'constructionStage', 'completionPercentage', 'notes', 'photos', 'inspector', 'project_id']:
                if key in data:
                    setattr(update, key, data[key])
                    
            # Update timestamp and update_date
            update.timestamp = int(datetime.utcnow().timestamp())
            update.update_date = datetime.utcnow()
            
            db.session.commit()
            return jsonify({'id': update.id, 'message': 'Update modified successfully'})
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating construction update: {str(e)}")
            return jsonify({'error': 'An error occurred while updating the construction update.'}), 500

@app.route('/api/eligibility', methods=['POST'])
def api_eligibility():
    try:
        data = request.get_json()
        income = int(data.get('income', 0))
        is_resident = bool(data.get('is_resident'))
        owns_pucca_house = bool(data.get('owns_pucca_house'))
        has_other_benefits = bool(data.get('has_other_benefits'))
        family_members = int(data.get('family_members', 1))
        scheme = data.get('scheme', 'pmay').lower()
    except Exception:
        return jsonify({'eligible': False, 'message': 'Invalid input.'}), 400
        
    # Enhanced eligibility criteria
    income_per_person = income / family_members if family_members > 0 else income
    
    # Different criteria based on scheme
    if scheme == 'pmay':
        income_limit = 300000
        per_capita_limit = 75000
    else:  # SGAY
        income_limit = 250000
        per_capita_limit = 60000
    
    if (
        income <= income_limit and
        income_per_person <= per_capita_limit and
        is_resident and
        not owns_pucca_house and
        not has_other_benefits
    ):
        scheme_name = 'PMAY' if scheme == 'pmay' else 'SGAY'
        return jsonify({
            'eligible': True, 
            'message': f'You are eligible for {scheme_name} Sikkim.',
            'next_steps': 'Please register and submit your application with all required documents.'
        })
    else:
        reasons = []
        if income > income_limit:
            reasons.append(f"Annual household income exceeds ₹{income_limit//1000:,}0,000")
        if income_per_person > per_capita_limit:
            reasons.append(f"Per capita income exceeds ₹{per_capita_limit:,}")
        if not is_resident:
            reasons.append("Not a resident of Sikkim")
        if owns_pucca_house:
            reasons.append("Already owns a pucca house")
        if has_other_benefits:
            reasons.append("Already availed housing benefits under another scheme")
            
        return jsonify({
            'eligible': False, 
            'message': 'You are not eligible based on the provided criteria.',
            'reasons': reasons
        })

@app.route('/api/notifications', methods=['GET', 'PUT'])
@login_required
def api_notifications():
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        try:
            notifications = Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).all()
            return jsonify([
                {
                    'id': n.id,
                    'title': n.title,
                    'message': n.message,
                    'is_read': n.is_read,
                    'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S')
                } for n in notifications
            ])
        except Exception as e:
            logger.error(f"Error fetching notifications: {str(e)}")
            return jsonify({'error': 'An error occurred while fetching notifications.'}), 500
            
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            notification_id = data.get('id')
            
            if not notification_id:
                # Mark all as read
                Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
                db.session.commit()
                return jsonify({'success': True, 'message': 'All notifications marked as read'})
            else:
                # Mark specific notification as read
                notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
                if not notification:
                    return jsonify({'error': 'Notification not found'}), 404
                    
                notification.is_read = True
                db.session.commit()
                return jsonify({'success': True, 'message': 'Notification marked as read'})
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating notifications: {str(e)}")
            return jsonify({'error': 'An error occurred while updating notifications.'}), 500

@app.route('/api/stats', methods=['GET'])
def api_stats():
    try:
        # Get overall statistics
        total_projects = Project.query.count()
        completed_projects = Project.query.filter_by(status="Completed").count()
        in_progress_projects = Project.query.filter_by(status="In Progress").count()
        pending_projects = Project.query.filter_by(status="Pending").count()
        total_beneficiaries = Beneficiary.query.count()
        
        # Get district-wise statistics
        districts = ["East Sikkim", "West Sikkim", "North Sikkim", "South Sikkim"]
        district_stats = {}
        
        for district in districts:
            district_projects = Project.query.filter_by(district=district).count()
            district_completed = Project.query.filter_by(district=district, status="Completed").count()
            district_beneficiaries = Beneficiary.query.filter_by(district=district).count()
            
            completion_rate = (district_completed / district_projects * 100) if district_projects > 0 else 0
            
            district_stats[district] = {
                'total_projects': district_projects,
                'completed_projects': district_completed,
                'beneficiaries': district_beneficiaries,
                'completion_rate': round(completion_rate, 1)
            }
        
        # Get monthly progress data for chart
        current_year = datetime.utcnow().year
        monthly_data = []
        
        for month in range(1, 13):
            # This is simplified - in a real app, you'd use actual date fields
            # For demo purposes, we'll generate random data
            if month <= datetime.utcnow().month:
                monthly_data.append({
                    'month': month,
                    'completed': random.randint(5, 15) if month < datetime.utcnow().month else completed_projects,
                    'in_progress': random.randint(10, 25) if month < datetime.utcnow().month else in_progress_projects
                })
        
        return jsonify({
            'overall': {
                'total_projects': total_projects,
                'completed_projects': completed_projects,
                'in_progress_projects': in_progress_projects,
                'pending_projects': pending_projects,
                'total_beneficiaries': total_beneficiaries,
                'completion_rate': round((completed_projects / total_projects * 100), 1) if total_projects > 0 else 0
            },
            'districts': district_stats,
            'monthly_data': monthly_data
        })
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        return jsonify({'error': 'An error occurred while fetching statistics.'}), 500

@app.route('/api/contact', methods=['POST'])
def api_contact():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        subject = data.get('subject')
        message = data.get('message')
        
        if not name or not email or not message:
            return jsonify({'success': False, 'message': 'Please fill all required fields.'}), 400
        
        # In a real application, you would send an email or store the contact message
        # For now, we'll just return a success message
        
        return jsonify({
            'success': True,
            'message': 'Your message has been sent successfully. We will get back to you soon.'
        })
    except Exception as e:
        logger.error(f"Error processing contact form: {str(e)}")
        return jsonify({'success': False, 'message': 'An error occurred while sending your message.'}), 500

# Add a test route to list beneficiary IDs for OTP testing
@app.route('/api/test/beneficiaries')
def test_beneficiaries():
    """Test endpoint to list beneficiary IDs for OTP testing"""
    try:
        # Only allow in development mode
        if app.config.get('ENV') != 'production':
            beneficiaries = Beneficiary.query.limit(5).all()
            return jsonify({
                'success': True,
                'message': 'Sample beneficiary IDs for testing',
                'data': [{'id': b.beneficiary_id, 'name': b.name} for b in beneficiaries]
            })
        return jsonify({'success': False, 'message': 'Endpoint disabled in production'}), 403
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Add a development-only route for testing OTP
@app.route('/test/otp')
def test_otp_page():
    """Development-only route for testing OTP functionality"""
    # Only allow in development mode
    if app.config.get('ENV') == 'production':
        abort(404)
    return render_template('test_otp.html')

# Configure Google AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/chat', methods=['POST'])
def chat():
    app.logger.info("Chat route hit")
    try:
        message = request.json.get('message')
        app.logger.info(f"Received message: {message}")

        if not message:
            app.logger.warning("No message provided by client")
            return jsonify({'error': 'No message provided'}), 400

        context = """
        You are a friendly and helpful assistant for the SGAY Sikkim (Sikkim Garib Awas Yojana) website. 
        Your main purpose is to help people, especially those in villages, understand and use this website and the SGAY housing scheme.
        Please use simple, clear language and explain things patiently. Avoid technical terms as much as possible, or explain them very simply if you must use them.

        About the SGAY Scheme and this Website:
        - SGAY is a housing scheme by the Sikkim Government to help poor people in Sikkim build houses.
        - This website helps people learn about SGAY, check if they are eligible, apply for the scheme, and see the progress of applications and house construction.

        You can help users with questions about:
        1.  The SGAY Scheme: 
            - What is SGAY? Who is it for?
            - Eligibility: Who can apply? (e.g., income, residency, current housing).
            - Application Process: How to apply? What forms or documents are needed?
            - Documents: What papers are required (like income certificate, Aadhar, land documents, photos)?
            - Status: How to check the status of an application or house construction.
        2.  Using this Website:
            - Finding Information: How to find scheme guidelines, project lists, or contact details.
            - Registration and Login: How to create an account or log in.
            - Viewing Progress: How to see updates on projects or applications.
            - Map: How to use the map to see where houses are being built.
            - Beneficiary Lists: How to find lists of people who have received help.
            - Profile: How to view or update their profile information after logging in.
            - Notifications: Understanding notifications they might receive.
        3.  General Questions: You can also try to answer general, everyday questions if the user asks. Be a friendly guide.

        Important: 
        - If you don't know the answer to something specific about the scheme that isn't covered here, suggest they contact the Rural Development Department or check official government announcements.
        - Be polite and encouraging. Many users may not be familiar with computers or government schemes.
        - Keep your answers as short and simple as possible while still being helpful.
        """

        prompt = f"{context}\n\nUser: {message}\nAssistant:"
        app.logger.info("Sending prompt to Google AI")
        
        ai_response = model.generate_content(prompt)
        
        app.logger.info(f"Raw AI response object: {ai_response}")
        response_text = None
        try:
            if ai_response.parts:
                response_text = ai_response.parts[0].text
            elif hasattr(ai_response, 'text'):
                 response_text = ai_response.text
            else:
                app.logger.warning(f"AI response does not have .text or .parts attribute. Full response: {ai_response}")
        except Exception as e:
            app.logger.error(f"Error accessing AI response text: {str(e)}. Full response: {ai_response}")

        app.logger.info(f"Extracted AI response text: {response_text}")
        
        if response_text is None:
            app.logger.warning("AI model returned None or empty response text.")
            response_text = "I'm sorry, I could not generate a response at this moment. Please try asking in a different way."

        app.logger.info(f"Sending back to client: {{'response': {response_text}}}")
        return jsonify({'response': response_text})
    except Exception as e:
        app.logger.error(f"Chat error: {str(e)}", exc_info=True)
        return jsonify({'error': 'An error occurred processing your request'}), 500

if __name__ == '__main__':
    # setup_database() # We'll run initialization via CLI command now
    app.run(debug=True)
