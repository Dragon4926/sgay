from flask import jsonify, request, session, render_template, redirect, flash
from . import auth_bp
from app import db, logger, app
from datetime import datetime, timedelta, timezone
import random
from models import User, Beneficiary
from werkzeug.security import check_password_hash, generate_password_hash
from flask import url_for

def generate_otp():
    """Generate a 6-digit OTP"""
    return str(random.randint(100000, 999999))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login_page():
    if session.get('user_id'):
        flash('You are already logged in.', 'info')
        user_role = session.get('user_role', 'beneficiary')
        if user_role.lower() in ['admin', 'nodal_officer']:
            return redirect(url_for('admin.admin_dashboard'))
        else:
            return redirect(url_for('beneficiary.dashboard'))
            
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role_selected = request.form.get('role')
        
        if not username or not password or not role_selected:
            flash('Username, password, and role are required.', 'error')
            return render_template('login.html', username=username, selected_role=role_selected)
        
        if role_selected not in ['admin', 'Nodal Officer']:
            flash('Invalid role selected for this login form. Beneficiaries should use "Login with OTP".', 'error')
            return render_template('login.html', username=username, selected_role=role_selected)

        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.role.lower() == role_selected.lower():
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            user.last_login = datetime.now(timezone.utc)
            user.login_attempts = 0  # Reset login attempts on successful login
            try:
                db.session.add(user)
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error updating last_login for user {user.username}: {str(e)}")

            flash('Login successful!', 'success')
            if user.role.lower() == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            elif user.role.lower() == 'nodal officer':
                return redirect(url_for('admin.nodal_officer_dashboard'))
            else:
                return redirect(url_for('beneficiary.dashboard'))
        else:
            if user and user.role.lower() != role_selected.lower():
                flash(f"Login failed. User '{username}' is not registered as a {role_selected.capitalize()}.", 'error')
            else:
                flash('Invalid username or password for the selected role.', 'error')
            # Implement login attempt tracking
            if user:
                user.login_attempts = (user.login_attempts or 0) + 1
                user.last_failed_login = datetime.utcnow()
                db.session.commit()
            return render_template('login.html', username=username, selected_role=role_selected)

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register_page():
    if session.get('user_id'):
        flash('You are already logged in.', 'info')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email') 
        phone_number = request.form.get('phone_number')

        if not username or not phone_number: 
            flash('Username and mobile number are required.', 'error')
            return render_template('register.html', username=username, email=email, phone_number=phone_number)

        if not (phone_number.isdigit() and len(phone_number) == 10):
            flash('Invalid mobile number. Please enter a 10-digit number.', 'error')
            return render_template('register.html', username=username, email=email, phone_number=phone_number)

        if email and ('@' not in email or '.' not in email): 
            flash('Invalid email address provided.', 'error')
            return render_template('register.html', username=username, email=email, phone_number=phone_number)
        
        existing_user_by_username = User.query.filter_by(username=username).first()
        if existing_user_by_username:
            flash('Username already exists. Please choose a different one.', 'error')
            return render_template('register.html', email=email, phone_number=phone_number)

        if email:
            existing_user_by_email = User.query.filter_by(email=email).first()
            if existing_user_by_email:
                flash('Email address already registered. Please use a different one or log in.', 'error')
                return render_template('register.html', username=username, phone_number=phone_number)
        
        existing_user_by_phone = User.query.filter_by(phone_number=phone_number).first()
        if existing_user_by_phone:
            flash('Mobile number already registered. Please use a different one or try logging in.', 'error')
            return render_template('register.html', username=username, email=email)

        otp_code = generate_otp()
        logger.info(f"========= OTP for {phone_number}: {otp_code} =========")
        flash(f'[SIMULATED OTP for {phone_number}: {otp_code}] Enter this OTP on the next page.', 'info')

        # Temporary password for new users
        dummy_password = f'dummy_password_{otp_code}'
        
        try:
            new_user = User(
                username=username, 
                email=email, 
                phone_number=phone_number,
                role='beneficiary',
                otp=otp_code,
                otp_generated_at=datetime.now(timezone.utc)
            )
            new_user.set_password(dummy_password)
            
            db.session.add(new_user)
            db.session.commit()
            session['otp_user_id_to_verify'] = new_user.id
            return redirect(url_for('auth.verify_otp'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating user {username} for OTP registration: {str(e)}")
            flash('An error occurred while processing your registration. Please try again.', 'error')
            return render_template('register.html', username=username, email=email, phone_number=phone_number)

    return render_template('register.html')

@auth_bp.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    user_id_to_verify = session.get('otp_user_id_to_verify')
    if not user_id_to_verify:
        flash('No user pending OTP verification. Please register first.', 'warning')
        return redirect(url_for('auth.register_page'))

    user = User.query.get(user_id_to_verify)
    if not user or user.role.lower() != 'beneficiary':
        flash('Invalid user for OTP verification.', 'error')
        session.pop('otp_user_id_to_verify', None)
        return redirect(url_for('auth.register_page'))

    if request.method == 'POST':
        submitted_otp = request.form.get('otp')
        if not submitted_otp or not user.otp or not user.otp_generated_at:
            flash('Invalid request. Please try again or resend OTP.', 'error')
            return render_template('verify_otp.html', phone_to_verify=user.phone_number)

        otp_generated_time = user.otp_generated_at
        if otp_generated_time.tzinfo is None:
            otp_generated_time = otp_generated_time.replace(tzinfo=timezone.utc)

        if datetime.now(timezone.utc) > otp_generated_time + timedelta(minutes=5):
            flash('OTP has expired. Please request a new one.', 'error')
            user.otp = None
            user.otp_generated_at = None
            db.session.add(user)
            db.session.commit()
            return render_template('verify_otp.html', phone_to_verify=user.phone_number)

        if submitted_otp == user.otp:
            user.otp = None 
            user.otp_generated_at = None
            user.last_login = datetime.now(timezone.utc)
            db.session.add(user)
            db.session.commit()
            session.pop('otp_user_id_to_verify', None)
            session['user_id'] = user.id
            session['username'] = user.username
            session['user_role'] = user.role
            flash('Mobile number verified successfully! You are now logged in.', 'success')
            
            # Check if the beneficiary has applied yet
            if user.role.lower() == 'beneficiary':
                beneficiary = Beneficiary.query.filter_by(user_id=user.id).first()
                
                # If beneficiary has no application ID, direct them to apply
                if beneficiary and not beneficiary.beneficiary_id:
                    return redirect(url_for('beneficiary.apply_for_housing'))
                # If beneficiary has application, show status
                elif beneficiary and beneficiary.beneficiary_id:
                    return redirect(url_for('beneficiary.application_status'))
            
            return redirect(url_for('beneficiary.dashboard'))
        else:
            flash('Invalid OTP. Please try again.', 'error')
    
    return render_template('verify_otp.html', phone_to_verify=user.phone_number)

@auth_bp.route('/login-otp', methods=['GET', 'POST'])
def login_otp():
    if session.get('user_id'):
        flash('You are already logged in.', 'info')
        user_role = session.get('user_role', 'beneficiary')
        if user_role.lower() == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        elif user_role.lower() == 'nodal_officer':
            return redirect(url_for('admin.admin_dashboard'))
        else:
            return redirect(url_for('beneficiary.dashboard'))

    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        if not phone_number or not (phone_number.isdigit() and len(phone_number) == 10):
            flash('Please enter a valid 10-digit mobile number.', 'error')
            return render_template('login_otp.html', phone_number=phone_number)

        user = User.query.filter_by(phone_number=phone_number).first()
        if not user:
            flash('No account found with this mobile number. Please register first.', 'error')
            return render_template('login_otp.html', phone_number=phone_number)

        otp_code = generate_otp()
        user.otp = otp_code
        user.otp_generated_at = datetime.now(timezone.utc)

        try:
            db.session.add(user)
            db.session.commit()
            logger.info(f"========= OTP for {phone_number}: {otp_code} =========")
            flash(f'[SIMULATED OTP for {phone_number}: {otp_code}] Enter this OTP to login.', 'info')
            session['otp_user_id_to_verify'] = user.id
            return redirect(url_for('auth.verify_otp'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error generating OTP for user {user.username}: {str(e)}")
            flash('An error occurred while sending the OTP. Please try again.', 'error')
            return render_template('login_otp.html', phone_number=phone_number)

    return render_template('login_otp.html')

@auth_bp.route('/resend-otp', methods=['GET'])
def resend_otp():
    user_id_to_verify = session.get('otp_user_id_to_verify')
    if not user_id_to_verify:
        flash('No user pending OTP verification. Please start over.', 'warning')
        return redirect(url_for('auth.register_page'))

    user = User.query.get(user_id_to_verify)
    if not user:
        flash('Invalid user for OTP verification.', 'error')
        session.pop('otp_user_id_to_verify', None)
        return redirect(url_for('auth.register_page'))

    new_otp_code = generate_otp()
    user.otp = new_otp_code
    user.otp_generated_at = datetime.now(timezone.utc)

    try:
        db.session.add(user)
        db.session.commit()
        logger.info(f"========= RESENT OTP for {user.phone_number}: {new_otp_code} =========")
        flash(f'[SIMULATED OTP for {user.phone_number}: {new_otp_code}] Enter this new OTP.', 'info')
        return redirect(url_for('auth.verify_otp'))
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resending OTP for user {user.username}: {str(e)}")
        flash('An error occurred while resending the OTP. Please try again.', 'error')
        return redirect(url_for('auth.verify_otp'))

@auth_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('user_role', None)
    session.pop('last_activity', None)
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.login_page'))

# Legacy routes for compatibility
@auth_bp.route('/beneficiary-login')
def beneficiary_login_page():
    """Redirect to new OTP login page"""
    return redirect(url_for('auth.login_otp'))

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    """Legacy route for compatibility"""
    data = request.get_json()
    phone_number = data.get('phone_number')
    application_id = data.get('application_id')
    
    # If application_id is provided, try to find the user through beneficiary
    if application_id and not phone_number:
        beneficiary = Beneficiary.query.filter_by(beneficiary_id=application_id).first()
        if beneficiary and beneficiary.user_id:
            user = User.query.get(beneficiary.user_id)
            if user and user.phone_number:
                phone_number = user.phone_number
    
    if not phone_number:
        return jsonify({
            'success': False,
            'message': 'Mobile number is required.'
        }), 400
    
    user = User.query.filter_by(phone_number=phone_number).first()
    if not user:
        return jsonify({
            'success': False,
            'message': 'No account found with this mobile number.'
        }), 404
    
    otp_code = generate_otp()
    user.otp = otp_code
    user.otp_generated_at = datetime.now(timezone.utc)
    
    try:
        db.session.add(user)
        db.session.commit()
        logger.info(f"========= OTP for {phone_number}: {otp_code} =========")
        
        response_data = {
            'success': True,
            'message': 'OTP sent successfully to your registered mobile number.'
        }
        
        # Only in development mode, include OTP in response
        if app.config.get('ENV') != 'production':
            response_data['development_otp'] = otp_code
            
        return jsonify(response_data)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error sending OTP: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error sending OTP. Please try again.'
        }), 500

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp_api():
    """Legacy API route for verification"""
    data = request.get_json()
    otp = data.get('otp')
    application_id = data.get('application_id')
    phone_number = data.get('phone_number')
    
    if not otp:
        return jsonify({
            'success': False,
            'message': 'OTP is required.'
        }), 400
    
    # Find user either by phone or through beneficiary's application_id
    user = None
    if phone_number:
        user = User.query.filter_by(phone_number=phone_number).first()
    elif application_id:
        beneficiary = Beneficiary.query.filter_by(beneficiary_id=application_id).first()
        if beneficiary and beneficiary.user_id:
            user = User.query.get(beneficiary.user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found.'
        }), 404
    
    # Verify OTP
    if not user.otp or user.otp != otp:
        return jsonify({
            'success': False,
            'message': 'Invalid OTP.'
        }), 401
    
    # Check if OTP has expired (5 minutes)
    otp_generated_time = user.otp_generated_at
    if otp_generated_time.tzinfo is None:
        otp_generated_time = otp_generated_time.replace(tzinfo=timezone.utc)
        
    if datetime.now(timezone.utc) > otp_generated_time + timedelta(minutes=5):
        return jsonify({
            'success': False,
            'message': 'OTP has expired. Please request a new one.'
        }), 401
    
    # Clear OTP and update last login
    user.otp = None
    user.otp_generated_at = None
    user.last_login = datetime.now(timezone.utc)
    
    try:
        db.session.add(user)
        db.session.commit()
        
        # Log user in
        session['user_id'] = user.id
        session['username'] = user.username
        session['user_role'] = user.role
        session['last_activity'] = datetime.utcnow().timestamp()
        
        return jsonify({
            'success': True,
            'message': 'Login successful.',
            'redirect': url_for('beneficiary.dashboard'),
            'user': {
                'name': user.full_name or user.username,
                'role': user.role
            }
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error verifying OTP: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error verifying OTP. Please try again.'
        }), 500

@auth_bp.route('/beneficiary_login', methods=['POST'])
def beneficiary_login():
    """Legacy route that redirects to the new verify-otp API endpoint"""
    return verify_otp_api()
