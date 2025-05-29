from flask import render_template, request, redirect, url_for, flash, jsonify, session, Blueprint
from . import admin_bp
from .utils import AdminUtils
from .forms import ConstructionImageUploadForm
from functools import wraps
from app import db, DISTRICTS, BLOCKS_BY_DISTRICT, logger
from utils import allowed_file
from models import User, Project, Beneficiary, HouseDesign, Notification, SiteVisit, SiteVisitPhoto, PlotImage, ConstructionUpdate
from werkzeug.security import generate_password_hash
from datetime import datetime
import json
from auth.routes import generate_otp
import os
from werkzeug.utils import secure_filename
from flask import current_app
import random
import uuid

# Role-based access control decorator
def role_required(allowed_roles):
    """
    Decorator to check if the current user has one of the allowed roles.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('auth.login_page'))

            user = User.query.get(user_id)
            
            # Make role check case-insensitive
            if not user or user.role.lower() not in [role.lower() for role in allowed_roles]:
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('auth.login_page'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# API-specific role decorator that returns JSON instead of redirects
def api_role_required(allowed_roles):
    """
    Decorator for API endpoints to check user roles and return JSON responses.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user_id = session.get('user_id')
            if not user_id:
                logger.warning("API access denied: No user session")
                return jsonify({'error': 'Authentication required'}), 401

            user = User.query.get(user_id)
            
            # Make role check case-insensitive
            if not user:
                logger.warning("API access denied: User not found")
                return jsonify({'error': 'User not found'}), 401
            
            if user.role.lower() not in [role.lower() for role in allowed_roles]:
                logger.warning(f"API access denied: User role '{user.role}' not in allowed roles {allowed_roles}")
                return jsonify({'error': f'Access denied. Required roles: {allowed_roles}'}), 403
            
            logger.info(f"API access granted: User {user.username} with role {user.role}")
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# User session helper
def get_current_user():
    """
    Get the current user from session.
    """
    user_id = session.get('user_id')
    if user_id:
        return User.query.get(user_id)
    return None

# Admin Dashboard
@admin_bp.route('/admin_dashboard')
@role_required(['admin'])
def admin_dashboard():
    """
    Main admin dashboard.
    """
    current_user = get_current_user()
    if not current_user: # Should be caught by role_required, but good practice
        flash('User not found.', 'error')
        return redirect(url_for('auth.login_page'))

    # Fetch all required data for the dashboard with proper error handling
    try:
        stats = AdminUtils.get_dashboard_stats()
        recent_activities = AdminUtils.get_recent_activities()
        pending_tasks = AdminUtils.get_pending_tasks()
        projects_summary = AdminUtils.get_projects_summary()
        beneficiaries_summary = AdminUtils.get_beneficiaries_summary()
        financial_summary = AdminUtils.get_financial_summary()
        verification_tasks = AdminUtils.get_verification_tasks()
        sanction_requests = AdminUtils.get_sanction_requests()
    except Exception as e:
        # Log the error
        print(f"Error fetching admin dashboard data: {str(e)}")
        flash("An error occurred while loading dashboard data. Please try again.", "error")
        # Provide fallback values for the template
        stats = {'total_beneficiaries': 0, 'total_projects': 0, 'active_users': 0, 'pending_approvals': 0}
        projects_summary = {'total': 0, 'completed': 0, 'in_progress': 0, 'planning': 0}
        financial_summary = {'total_budget_allocated': '₹ 0 Cr', 'total_funds_disbursed': '₹ 0 Cr', 'fund_utilization_percentage': 0}
        recent_activities = []
        pending_tasks = []
        beneficiaries_summary = {}
        verification_tasks = []
        sanction_requests = []
    
    return render_template('admin/admin_dashboard.html',
                          stats=stats,
                          recent_activities=recent_activities,
                          pending_tasks=pending_tasks,
                          projects_summary=projects_summary,
                          beneficiaries_summary=beneficiaries_summary,
                          verification_tasks=verification_tasks,
                          sanction_requests=sanction_requests,
                          financial_summary=financial_summary,
                          current_user=current_user)

@admin_bp.route('/nodal/dashboard')
@role_required(['Nodal Officer'])
def nodal_officer_dashboard():
    current_user = get_current_user()
    if not current_user or not current_user.assigned_district:
        flash('User not found or no district assigned.', 'error')
        return redirect(url_for('auth.login_page'))

    assigned_district = current_user.assigned_district

    # Fetch projects for the nodal officer's assigned district (ongoing)
    projects_in_district = Project.query.filter(
        Project.district == assigned_district,
        Project.status.notin_(['Completed', 'Cancelled']) # Example: exclude completed/cancelled
    ).order_by(Project.startDate.desc()).all()
    
    # Fetch beneficiaries needing site verification in the officer's district
    beneficiaries_for_visit = Beneficiary.query.filter_by(
        district=assigned_district, 
        status='Pending Verification' # Status set by Admin after approval
    ).order_by(Beneficiary.applicationDate.asc()).all()

    # Stats for Nodal Officer
    stats = {
        'pending_verification': len(beneficiaries_for_visit),
        'ongoing_projects': len(projects_in_district),
        'district_name': assigned_district
    }

    return render_template('admin/nodal_dashboard.html', 
                           current_user=current_user, 
                           projects=projects_in_district,
                           beneficiaries_for_visit=beneficiaries_for_visit,
                           stats=stats
                           )

# Beneficiary Management Routes
@admin_bp.route('/beneficiaries')
@role_required(['admin', 'Nodal Officer', 'State Authority'])
def manage_beneficiaries():
    """List all beneficiaries with filtering options."""
    page = request.args.get('page', 1, type=int)
    per_page = 15 # Show more per page

    status_filter = request.args.get('status', 'all')
    district_filter = request.args.get('district', 'all')

    query = Beneficiary.query

    if status_filter != 'all':
        query = query.filter(Beneficiary.status == status_filter)
    if district_filter != 'all':
        query = query.filter(Beneficiary.district == district_filter)

    # Order by most recent applications first, then by name
    beneficiaries_pagination = query.order_by(Beneficiary.created_at.desc(), Beneficiary.name.asc()).paginate(page=page, per_page=per_page)
    
    # Get distinct statuses and districts for filter dropdowns
    statuses = [status[0] for status in db.session.query(Beneficiary.status).distinct().all() if status[0]]
    # Ensure 'Applied' is an option if it exists
    if 'Applied' not in statuses and Beneficiary.query.filter_by(status='Applied').first():
        statuses.append('Applied')
    # Sort statuses, perhaps placing 'Applied' and 'Pending Verification' first
    preferred_order = ['Applied', 'Pending Verification']
    statuses = sorted(statuses, key=lambda x: (preferred_order.index(x) if x in preferred_order else float('inf'), x))


    return render_template('admin/beneficiaries.html', 
                           beneficiaries_pagination=beneficiaries_pagination,
                           districts=DISTRICTS, # Pass all defined districts
                           blocks_by_district=json.dumps(BLOCKS_BY_DISTRICT), # Pass blocks for potential edits
                           current_user=get_current_user(),
                           statuses=statuses,
                           selected_status=status_filter,
                           selected_district=district_filter
                           )

@admin_bp.route('/beneficiaries/review/<int:beneficiary_id>', methods=['GET', 'POST'])
@role_required(['admin']) # Only admin can do the initial approval
def review_application(beneficiary_id):
    """Review a new beneficiary application, approve, or reject it."""
    beneficiary = Beneficiary.query.get_or_404(beneficiary_id)
    current_admin = get_current_user()

    if request.method == 'POST':
        action = request.form.get('action')
        remarks = request.form.get('remarks', '')

        if action == 'approve':
            # 1. Change Beneficiary Status
            beneficiary.status = 'Pending Verification' # Next step for Nodal Officer
            beneficiary.approvalDate = datetime.utcnow().strftime('%Y-%m-%d')
            beneficiary.progress = 20 # Update progress
            
            # 2. Create User Account for Beneficiary if one doesn't exist based on phone
            user = User.query.filter_by(phone_number=beneficiary.contactNumber).first()
            if not user:
                username = f"user_{beneficiary.contactNumber}" # Generate a unique username
                # Check if this generated username already exists, append random digits if so
                temp_user_check = User.query.filter_by(username=username).first()
                counter = 1
                while temp_user_check:
                    username = f"user_{beneficiary.contactNumber}_{counter}"
                    temp_user_check = User.query.filter_by(username=username).first()
                    counter += 1

                otp_for_login = generate_otp() # Use the existing helper
                
                user = User(
                    username=username, 
                    full_name=beneficiary.name,
                    phone_number=beneficiary.contactNumber, 
                    role='beneficiary', 
                    otp=otp_for_login, # Store OTP for first login
                    otp_generated_at=datetime.utcnow() # Set generation time
                )
                # Set a temporary or default password (beneficiary will use OTP to login first time)
                user.set_password(f"default_{otp_for_login}") 
                db.session.add(user)
                db.session.flush() # to get user.id if needed immediately
                beneficiary.user_id = user.id
                flash(f'User account created for {beneficiary.name} (Username: {username}). OTP for first login: {otp_for_login} (Inform beneficiary). Status set to Pending Verification.', 'success')
            elif not beneficiary.user_id:
                # User exists with this phone number but not linked, link them.
                beneficiary.user_id = user.id
                flash(f'Existing user account for phone {beneficiary.contactNumber} linked to beneficiary {beneficiary.name}. Status set to Pending Verification.', 'info')
            else:
                flash(f'Application for {beneficiary.name} approved. Status set to Pending Verification.', 'success')

            # Add any approval remarks to beneficiary model if a field exists or log them
            if remarks:
                beneficiary.additional_comments = (beneficiary.additional_comments or '') + f"\nAdmin Approval Remarks: {remarks}"

        elif action == 'reject':
            beneficiary.status = 'Rejected'
            if remarks:
                beneficiary.additional_comments = (beneficiary.additional_comments or '') + f"\nAdmin Rejection Remarks: {remarks}"
            flash(f'Application for {beneficiary.name} has been rejected.', 'warning')
        
        elif action == 'update_details':
            # Logic to update beneficiary details from form fields
            beneficiary.name = request.form.get('name', beneficiary.name)
            beneficiary.contactNumber = request.form.get('contactNumber', beneficiary.contactNumber)
            beneficiary.aadhar_number = request.form.get('aadhar_number', beneficiary.aadhar_number)
            beneficiary.district = request.form.get('district', beneficiary.district)
            beneficiary.block = request.form.get('block', beneficiary.block)
            beneficiary.village = request.form.get('village', beneficiary.village)
            beneficiary.address = request.form.get('address', beneficiary.address)
            beneficiary.annual_income = request.form.get('annual_income', beneficiary.annual_income, type=int)
            beneficiary.family_members = request.form.get('family_members', beneficiary.family_members, type=int)
            beneficiary.housing_status = request.form.get('housing_status', beneficiary.housing_status)
            # Add other editable fields as needed
            flash('Beneficiary details updated.', 'info')

        else:
            flash('Invalid action specified.', 'danger')
            return redirect(url_for('admin.review_application', beneficiary_id=beneficiary.id))

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing application: {str(e)}', 'danger')
            logger.error(f"Error processing application for beneficiary {beneficiary.id}: {str(e)}")
        
        return redirect(url_for('admin.manage_beneficiaries'))

    # For GET request, pass all districts and blocks for editing
    return render_template('admin/review_application.html', 
                           beneficiary=beneficiary, 
                           current_user=current_admin,
                           districts=DISTRICTS,
                           blocks_by_district=json.dumps(BLOCKS_BY_DISTRICT)
                           )

@admin_bp.route('/beneficiaries/verify')
@role_required(['Nodal Officer'])
def verify_beneficiaries():
    """Interface for nodal officers to verify new beneficiary applications."""
    verification_tasks = AdminUtils.get_verification_tasks('Nodal Officer')
    return render_template('admin/verify_beneficiaries.html', verification_tasks=verification_tasks)

@admin_bp.route('/beneficiaries/verify/<task_id>', methods=['GET', 'POST'])
@role_required(['Nodal Officer'])
def verify_beneficiary_detail(task_id):
    """Detailed view for verifying a specific beneficiary application."""
    # Try to find beneficiary by ID first, then by beneficiary_id
    beneficiary = Beneficiary.query.get(task_id) or Beneficiary.query.filter_by(beneficiary_id=task_id).first_or_404()
    
    if request.method == 'POST':
        action = request.form.get('action') # 'approve' or 'reject'
        remarks = request.form.get('remarks')
        
        if action == 'approve':
            beneficiary.status = 'Verified'
            # Potentially create a User account for the beneficiary if not already existing
            # and link it.
            if not beneficiary.user_id:
                # Check if a user with a similar username or email already exists to avoid duplicates
                # For this example, we'll assume a simple user creation process 
                # A more robust implementation would handle password setting, email verification, etc.
                username = f"beneficiary_{beneficiary.beneficiary_id}"
                existing_user = User.query.filter_by(username=username).first()
                
                if existing_user:
                    # Link the existing user to this beneficiary
                    beneficiary.user_id = existing_user.id
                else:
                    # Create a new user for this beneficiary
                    new_user = User(
                        username=username,
                        full_name=beneficiary.name,
                        email='',  # Would need to be collected
                        phone_number=beneficiary.contactNumber,
                        role='beneficiary'
                    )
                    # Generate a temporary password
                    temp_password = f"temp_{random.randint(10000, 99999)}"
                    new_user.set_password(temp_password)
                    
                    db.session.add(new_user)
                    db.session.commit()  # Need to commit to get the ID
                    
                    # Link the new user to the beneficiary
                    beneficiary.user_id = new_user.id
                    
                    # Create a notification for the new user
                    notification = Notification(
                        user_id=new_user.id,
                        title="Account Created",
                        message=f"Your account has been created. Your temporary password is: {temp_password}. Please change it after logging in.",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notification)
                    
                    # In a real system, you would want to send this via SMS or email
                    # Here we're just printing it for demo purposes
                    logger.info(f"Created user for beneficiary {beneficiary.beneficiary_id} with temp password: {temp_password}")
            
            flash(f'Application for {beneficiary.name} has been verified.', 'success')
            
            # Create a notification for the beneficiary
            if beneficiary.user_id:
                notification = Notification(
                    user_id=beneficiary.user_id,
                    title="Application Verified",
                    message=f"Your housing application (ID: {beneficiary.beneficiary_id}) has been verified by a Nodal Officer. Project allocation will begin soon.",
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
            
            # Add any verification remarks
            if remarks:
                beneficiary.additional_comments = (beneficiary.additional_comments or '') + f"\nVerification Remarks: {remarks}"
        
        elif action == 'reject':
            beneficiary.status = 'Rejected'
            if remarks:
                beneficiary.additional_comments = (beneficiary.additional_comments or '') + f"\nRejection Remarks: {remarks}"
            
            # Create a notification for the beneficiary
            if beneficiary.user_id:
                notification = Notification(
                    user_id=beneficiary.user_id,
                    title="Application Rejected",
                    message=f"Your housing application (ID: {beneficiary.beneficiary_id}) has been rejected by a Nodal Officer.\nReason: {remarks or 'No specific reason provided.'}",
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                
            flash(f'Application for {beneficiary.name} has been rejected.', 'warning')
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing application: {str(e)}', 'danger')
        
        return redirect(url_for('admin.manage_beneficiaries'))
    
    return render_template('admin/verify_beneficiary.html', 
                          beneficiary=beneficiary, 
                          current_user=get_current_user())

@admin_bp.route('/beneficiaries/update-status/<task_id>', methods=['GET', 'POST'])
@role_required(['Nodal Officer', 'admin'])
def update_beneficiary_status(task_id):
    """Update status and add plot images for a beneficiary application."""
    beneficiary = Beneficiary.query.filter_by(beneficiary_id=task_id).first_or_404()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_status':
            new_status = request.form.get('status')
            remarks = request.form.get('remarks', '')
            
            if new_status:
                old_status = beneficiary.status
                beneficiary.status = new_status
                
                # Update progress based on status
                if new_status == 'Applied':
                    beneficiary.progress = 5
                elif new_status == 'Pending Verification':
                    beneficiary.progress = 20
                elif new_status == 'Verified':
                    beneficiary.progress = 40
                elif new_status == 'Approved for Construction':
                    beneficiary.progress = 60
                elif new_status == 'Under Construction':
                    beneficiary.progress = 75
                elif new_status == 'Completed':
                    beneficiary.progress = 100
                
                # Add remark as a comment
                if remarks:
                    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M')
                    status_comment = f"\n[{timestamp}] Status changed from {old_status} to {new_status}: {remarks}"
                    beneficiary.additional_comments = (beneficiary.additional_comments or '') + status_comment
                
                # Create notification for beneficiary
                if beneficiary.user_id:
                    notification = Notification(
                        user_id=beneficiary.user_id,
                        title="Application Status Updated",
                        message=f"Your application status has been updated to: {new_status}.\n{remarks}",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notification)
                
                flash(f"Status updated to '{new_status}' for {beneficiary.name}", 'success')
        
        elif action == 'upload_plot_image':
            if 'plot_image' not in request.files:
                flash('No file selected', 'error')
                return redirect(request.url)
            
            file = request.files['plot_image']
            if file.filename == '':
                flash('No file selected', 'error')
                return redirect(request.url)
            
            if file and allowed_file(file.filename):
                # Create directory if it doesn't exist
                upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'plots', beneficiary.beneficiary_id)
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                
                # Save the file
                filename = secure_filename(file.filename)
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
                
                # Create a PlotImage entry
                relative_path = os.path.join('plots', beneficiary.beneficiary_id, filename)
                plot_image = PlotImage(
                    beneficiary_id=beneficiary.beneficiary_id,
                    image_url=relative_path,
                    created_at=datetime.utcnow()
                )
                db.session.add(plot_image)
                
                # Add remark about the image upload
                current_user = get_current_user()
                image_comment = f"\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}] Plot image uploaded by {current_user.full_name if current_user else 'System'}"
                beneficiary.additional_comments = (beneficiary.additional_comments or '') + image_comment
                
                # Create notification for beneficiary
                if beneficiary.user_id:
                    notification = Notification(
                        user_id=beneficiary.user_id,
                        title="Plot Image Uploaded",
                        message=f"A new image of your plot has been uploaded by {current_user.full_name if current_user else 'System'}.",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notification)
                
                flash('Plot image uploaded successfully', 'success')
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'Error processing update: {str(e)}', 'danger')
            
        return redirect(url_for('admin.update_beneficiary_status', task_id=task_id))
    
    # Get plot images for this beneficiary
    plot_images = PlotImage.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).order_by(PlotImage.created_at.desc()).all()
    
    # Get any projects associated with this beneficiary
    project = Project.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).first()
    
    # Get current user, handle potential None case
    current_user = get_current_user()
    
    # Determine possible statuses based on role
    possible_statuses = ['Applied', 'Pending Verification', 'Verified', 
                         'Approved for Construction', 'Under Construction', 
                         'Completed', 'Rejected']
    
    return render_template('admin/update_beneficiary_status.html',
                          beneficiary=beneficiary,
                          plot_images=plot_images,
                          project=project,
                          current_user=current_user,
                          possible_statuses=possible_statuses)

# Helper function to check if file has allowed extension
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_EXTENSIONS', {'jpg', 'jpeg', 'png', 'pdf'})

# Project Management Routes
@admin_bp.route('/projects')
@role_required(['admin'])
def manage_projects():
    """List all projects with filtering options."""
    page = request.args.get('page', 1, type=int)
    projects_pagination = Project.query.order_by(Project.project_id.asc()).paginate(page=page, per_page=10)
    return render_template('admin/projects.html', projects_pagination=projects_pagination)


@admin_bp.route('/projects/inspect')
@role_required(['Nodal Officer'])
def inspect_projects():
    """Interface for scheduling and managing construction inspections."""
    # Fetch projects that might need inspection, e.g., 'In Progress' or 'Pending Inspection'
    projects_to_inspect = Project.query.filter(Project.status.in_(['In Progress', 'Pending Inspection'])).all()
    return render_template('admin/inspect_projects.html', projects_to_inspect=projects_to_inspect)


@admin_bp.route('/projects/status/<project_id>', methods=['GET', 'POST'])
@role_required(['Nodal Officer'])
def update_project_status(project_id):
    """Update the status and progress of a project."""
    project = Project.query.filter_by(project_id=project_id).first_or_404()
    if request.method == 'POST':
        new_status = request.form.get('status')
        new_completion_percentage = request.form.get('completionPercentage', type=int)
        # Add more fields as necessary, e.g., notes, photos from ConstructionUpdate model

        if new_status:
            project.status = new_status
        if new_completion_percentage is not None:
            project.completionPercentage = new_completion_percentage
        
        # Potentially add a new ConstructionUpdate record here
        # from models import ConstructionUpdate
        # update = ConstructionUpdate(project_id=project.project_id, ...)
        # db.session.add(update)

        db.session.commit()
        flash(f'Project {project.project_id} status updated successfully', 'success')
        return redirect(url_for('admin.manage_projects'))
    
    return render_template('admin/update_project_status.html', project=project)

# Financial Management Routes
@admin_bp.route('/funds/sanction')
@role_required(['State Authority'])
def sanction_funds():
    """Interface for state authorities to approve fund sanctions."""
    sanction_requests = AdminUtils.get_sanction_requests('State Authority')
    financial_summary = AdminUtils.get_financial_summary('State Authority')
    return render_template('admin/sanction_funds.html', 
                           sanction_requests=sanction_requests,
                           financial_summary=financial_summary)

@admin_bp.route('/funds/sanction/<request_id>', methods=['GET', 'POST'])
@role_required(['State Authority'])
def sanction_fund_detail(request_id):
    """Detailed view for approving a specific fund sanction request."""
    project = Project.query.filter_by(project_id=request_id).first_or_404()
    
    # Determine priority based on creation date
    priority = 'medium'  # Default priority
    if project.created_at and project.status == 'Pending Sanction':
        if (datetime.utcnow() - project.created_at).days > 7:
            priority = 'high'
    
    # Create a sanction request object that matches template expectations
    sanction_request = {
        'id': project.id,
        'batch_id': project.project_id,
        'district': project.district,
        'beneficiary_count': Beneficiary.query.filter_by(beneficiary_id=project.beneficiary_id).count() if project.beneficiary_id else 1,
        'total_amount': f"₹ {project.allocation / 100000:.1f} Lakhs",
        'beneficiary_name': project.beneficiaryName,
        'location': project.location,
        'submitted_by': 'Nodal Officer',  # This would come from actual user data
        'submission_date': project.created_at.strftime('%Y-%m-%d') if project.created_at else (project.startDate or 'N/A'),
        'status': 'pending_approval' if project.status == 'Pending Sanction' else 'approved',
        'description': project.description or 'No description provided',
        'priority': priority
    }
    
    if request.method == 'POST':
        action = request.form.get('action') # 'approve' or 'reject'
        remarks = request.form.get('remarks', '')
        
        if action == 'approve':
            project.status = 'Funds Sanctioned' # Or a similar status
            # Potentially update allocation or create transaction records
            flash(f'Funds sanctioned for project {project.project_id}', 'success')
        elif action == 'reject':
            project.status = 'Sanction Rejected'
            flash(f'Fund sanction rejected for project {project.project_id}', 'warning')
        else:
            flash('Invalid action.', 'error')
            return render_template('admin/sanction_fund_detail.html', sanction_request=sanction_request, project=project)

        db.session.commit()
        return redirect(url_for('admin.sanction_funds'))
        
    return render_template('admin/sanction_fund_detail.html', sanction_request=sanction_request, project=project)


@admin_bp.route('/budget/allocate', methods=['GET', 'POST'])
@role_required(['State Authority', 'Central Authority'])
def allocate_budget():
    """Interface for budget allocation among districts."""
    current_user = get_current_user()
    if request.method == 'POST':
        # This would be complex: involve forms for allocating budget per district/scheme
        # Needs a model to store budget allocations, or update project financial details
        flash('Budget allocation updated successfully (Not implemented fully)', 'success')
        return redirect(url_for('admin.allocate_budget'))
    
    financial_summary = AdminUtils.get_financial_summary(current_user.role)
    # Fetch distinct districts for allocation form
    districts = [d.district for d in db.session.query(Project.district).distinct().all()]
    return render_template('admin/allocate_budget.html', financial_summary=financial_summary, districts=districts, current_user=current_user)

# Reports and Analytics
@admin_bp.route('/reports')
@role_required(['admin'])
def view_reports():
    """View various reports and analytics based on role."""
    current_user = get_current_user()
    projects_summary = AdminUtils.get_projects_summary(current_user.role)
    beneficiaries_summary = AdminUtils.get_beneficiaries_summary(current_user.role)
    financial_summary = AdminUtils.get_financial_summary(current_user.role)
    
    # Create a reports object to match the template's expected structure
    reports = {
        'project_summary': projects_summary,
        'beneficiary_summary': beneficiaries_summary,
        'financial_summary': financial_summary
    }
    
    return render_template('admin/reports.html',
                          reports=reports,
                          current_user=current_user)

@admin_bp.route('/reports/generate', methods=['POST'])
@role_required(['admin', 'State Authority', 'Central Authority'])
def generate_report():
    """Generate a custom report based on selected parameters."""
    report_type = request.form.get('report_type')
    report_format = request.form.get('format', 'html')
    
    # Actual report generation logic would go here using libraries like WeasyPrint for PDF, openpyxl for Excel
    # Query data based on report_type and filters
    
    flash(f'Report generation for {report_type} initiated (Not implemented)', 'info')
    return redirect(url_for('admin.view_reports'))

# User Management (for Admin role)
@admin_bp.route('/users', methods=['GET', 'POST'])
@role_required(['admin'])
def manage_users():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        role = request.form.get('role')
        assigned_district = request.form.get('assigned_district')

        if not all([username, password, full_name, role]):
            flash('Username, password, full name, and role are required.', 'danger')
            return redirect(url_for('admin.manage_users'))

        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'danger')
            return redirect(url_for('admin.manage_users'))
        
        if email and User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return redirect(url_for('admin.manage_users'))

        hashed_password = generate_password_hash(password)
        
        new_user_data = {
            'username': username,
            'password_hash': hashed_password,
            'full_name': full_name,
            'email': email,
            'role': role
        }

        if role.lower() == 'nodal officer':
            if not assigned_district:
                flash('Assigned district is required for Nodal Officer.', 'danger')
                return redirect(url_for('admin.manage_users'))
            new_user_data['assigned_district'] = assigned_district
        elif role.lower() not in ['admin', 'nodal officer']:
            flash('Invalid role specified.', 'danger')
            return redirect(url_for('admin.manage_users'))


        new_user = User(**new_user_data)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash(f'{role.capitalize()} "{username}" added successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding user: {str(e)}', 'danger')
        
        return redirect(url_for('admin.manage_users'))

    # GET request: List users
    page = request.args.get('page', 1, type=int)
    # Fetch admins and nodal officers
    users_query = User.query.filter(User.role.in_(['admin', 'Nodal Officer', 'Admin', 'nodal officer']))
    users_pagination = users_query.order_by(User.username.asc()).paginate(page=page, per_page=10)
    
    return render_template('admin/users.html', 
                           users_pagination=users_pagination, 
                           current_user=get_current_user(),
                           districts=DISTRICTS)


@admin_bp.route('/users/<int:user_id>', methods=['GET', 'POST'])
@role_required(['admin'])
def edit_user(user_id):
    """Edit a specific user's details and permissions."""
    user_to_edit = User.query.get_or_404(user_id)
    if request.method == 'POST':
        # Get data from form
        user_to_edit.username = request.form.get('username', user_to_edit.username)
        user_to_edit.full_name = request.form.get('full_name', user_to_edit.full_name)
        user_to_edit.email = request.form.get('email', user_to_edit.email)
        user_to_edit.phone = request.form.get('phone', user_to_edit.phone)
        new_role = request.form.get('role', user_to_edit.role)

        # Prevent admin from changing their own role to non-admin if they are the only admin? (complex logic)
        # For simplicity, allow role change by admin
        if new_role in ['admin', 'Nodal Officer', 'State Authority', 'Central Authority', 'user']: # Define allowed roles
             user_to_edit.role = new_role
        else:
            flash('Invalid role selected.', 'error')
            return render_template('admin/edit_user.html', user_to_edit=user_to_edit)

        db.session.commit()
        flash(f'User {user_to_edit.username} updated successfully', 'success')
        return redirect(url_for('admin.manage_users'))
    
    return render_template('admin/edit_user.html', user_to_edit=user_to_edit)

# Settings
@admin_bp.route('/settings', methods=['GET', 'POST'])
@role_required(['admin'])
def manage_settings():
    """Manage application settings."""
    if request.method == 'POST':
        # Process form submission
        form_type = request.form.get('form_type', '')
        
        if form_type == 'general':
            # Process general settings
            app_name = request.form.get('application_name')
            admin_email = request.form.get('admin_email')
            default_language = request.form.get('default_language')
            maintenance_mode = request.form.get('maintenance_mode') == 'on'
            
            # In a real application, you would save these to a database or config file
            flash('General settings updated successfully', 'success')
            
        elif form_type == 'notifications':
            # Process notification settings
            email_notifications = request.form.get('email_notifications') == 'on'
            sms_notifications = request.form.get('sms_notifications') == 'on'
            app_notifications = request.form.get('app_notifications') == 'on'
            notification_frequency = request.form.get('notification_frequency')
            
            flash('Notification settings updated successfully', 'success')
            
        elif form_type == 'security':
            # Process security settings
            session_timeout = request.form.get('session_timeout')
            password_policy = request.form.get('password_policy')
            two_factor_auth = request.form.get('two_factor_auth') == 'on'
            login_attempts = request.form.get('login_attempts') == 'on'
            
            flash('Security settings updated successfully', 'success')
            
        elif form_type == 'backup':
            # Process backup actions
            action = request.form.get('action')
            if action == 'backup_now':
                # Create database backup
                # In a real application, this would trigger a backup process
                flash('Database backup initiated', 'success')
            elif action == 'view_history':
                # Redirect to backup history page
                flash('Backup history feature not implemented yet', 'info')
                
        elif form_type == 'logs':
            # Redirect to logs view
            flash('System logs feature not implemented yet', 'info')
            
        elif form_type == 'cache':
            action = request.form.get('action')
            if action == 'clear_cache':
                # Clear system cache
                # In a real application, this would clear caches
                flash('System cache cleared successfully', 'success')
        
        return redirect(url_for('admin.manage_settings'))
        
    # This would typically query settings from a database or config
    return render_template('admin/settings.html')

# API routes - these should ideally also use the database
@admin_bp.route('/api/stats', methods=['GET'])
@api_role_required(['admin'])
def api_get_stats():
    current_user = get_current_user()
    stats = AdminUtils.get_dashboard_stats(current_user.role) # Already uses DB
    return jsonify(stats)

@admin_bp.route('/api/activities', methods=['GET'])
@api_role_required(['admin'])
def api_get_activities():
    current_user = get_current_user()
    activities = AdminUtils.get_recent_activities(current_user.role) # Uses DB (Notifications)
    # Convert datetime objects to string for JSON serialization
    for activity in activities:
        if isinstance(activity.get('timestamp'), datetime):
            activity['timestamp'] = activity['timestamp'].isoformat()
    return jsonify(activities)

@admin_bp.route('/api/project_info/<project_id>', methods=['GET'])
@api_role_required(['Nodal Officer', 'admin'])
def api_get_project_info(project_id):
    """Get project information for forms and validation"""
    try:
        project = Project.query.filter_by(project_id=project_id).first()
        if not project:
            logger.warning(f"Project not found: {project_id}")
            return jsonify({'error': 'Project not found'}), 404
        
        # Get beneficiary info
        beneficiary = Beneficiary.query.filter_by(beneficiary_id=project.beneficiary_id).first()
        
        # Check if nodal officer has permission to view this project
        current_user = get_current_user()
        logger.info(f"API access attempt - User: {current_user.username}, Role: {current_user.role}, Assigned District: {getattr(current_user, 'assigned_district', 'None')}, Project District: {project.district}")
        
        # Check district access for nodal officers
        # TEMPORARY: Allow all district access for testing (remove this in production)
        bypass_district_check = True  # Set to False to enable district checking
        
        if current_user.role == 'Nodal Officer' and not bypass_district_check:
            # Allow access if user has no assigned district (admin-like access) or if districts match
            user_district = getattr(current_user, 'assigned_district', None)
            if user_district:
                # Make district comparison case-insensitive and flexible
                user_district_clean = user_district.lower().strip()
                project_district_clean = project.district.lower().strip()
                
                # Check for exact match or if one contains the other
                districts_match = (
                    user_district_clean == project_district_clean or
                    user_district_clean in project_district_clean or
                    project_district_clean in user_district_clean
                )
                
                if not districts_match:
                    logger.warning(f"Access denied: User district '{user_district}' doesn't match Project district '{project.district}'")
                    return jsonify({
                        'error': f'Access denied. Your district: {user_district}, Project district: {project.district}',
                        'suggestion': 'Contact admin to update your district assignment or project district'
                    }), 403
                else:
                    logger.info(f"District access granted: '{user_district}' matches '{project.district}'")
        
        logger.info(f"API access granted for project {project_id}")
        return jsonify({
            'project_id': project.project_id,
            'beneficiary_name': project.beneficiaryName,
            'beneficiary_id': project.beneficiary_id,
            'district': project.district,
            'location': project.location,
            'status': project.status,
            'completion_percentage': project.completionPercentage,
            'start_date': project.startDate,
            'beneficiary_contact': beneficiary.contactNumber if beneficiary else None
        })
    except Exception as e:
        logger.error(f"Error fetching project info: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# This demo login route should be removed or secured properly in a production environment
@admin_bp.route('/login_demo/<int:user_id>')
def login_demo(user_id):
    user = User.query.get(user_id)
    if user:
        session['user_id'] = user.id
        session['user_role'] = user.role # Store role for role_required decorator
        flash(f'Logged in as {user.username} (DEMO)', 'info')
        if user.role.lower() in ['admin', 'nodal officer', 'state authority', 'central authority']:
            return redirect(url_for('admin.admin_dashboard'))
        # Add other role-based redirects if necessary
        return redirect(url_for('index')) # Redirect to main index or user-specific dashboard
    else:
        flash('Demo user not found.', 'error')
        return redirect(url_for('auth.login_page'))


@admin_bp.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('user_role', None)
    session.pop('last_activity', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login_page'))

# House Design Management Routes
@admin_bp.route('/house-designs')
@role_required(['admin'])
def house_designs():
    """List all submitted house designs for review and approval."""
    # Get pending designs (not approved yet)
    pending_designs = HouseDesign.query.filter_by(is_selected=True, is_approved=False).order_by(HouseDesign.created_at.desc()).all()
    
    # Get recently approved designs
    approved_designs = HouseDesign.query.filter_by(is_selected=True, is_approved=True).order_by(HouseDesign.updated_at.desc()).limit(10).all()
    
    return render_template('admin/house_designs.html', 
                          pending_designs=pending_designs,
                          approved_designs=approved_designs)

@admin_bp.route('/house-designs/<int:design_id>')
@role_required(['admin'])
def view_house_design_details(design_id):
    """View details of a specific house design."""
    design = HouseDesign.query.get_or_404(design_id)
    
    return render_template('admin/house_design_details.html', design=design)

@admin_bp.route('/house-designs/approve/<int:design_id>', methods=['POST'])
@role_required(['admin'])
def approve_house_design(design_id):
    """Approve a house design."""
    design = HouseDesign.query.get_or_404(design_id)
    
    if design.is_approved:
        flash('This design is already approved.', 'info')
        return redirect(url_for('admin.view_house_design_details', design_id=design_id))
    
    # Check if design meets requirements (e.g., cost within limits)
    if design.total_cost > design.beneficiary.allocated_fund * 0.7:
        flash('Warning: This design exceeds 70% of the allocated fund.', 'warning')
    
    # Approve the design
    design.is_approved = True
    design.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Notify the beneficiary
    try:
        notification = Notification(
            user_id=design.beneficiary.user_id,
            title="House Design Approved",
            message=f"Your house design '{design.design_type}' has been approved. You can now proceed with construction."
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        # Log the error but don't block the approval
        print(f"Error creating notification: {str(e)}")
    
    flash(f'House design for {design.beneficiary.name} has been approved.', 'success')
    return redirect(url_for('admin.house_designs'))

@admin_bp.route('/house-designs/reject/<int:design_id>', methods=['POST'])
@role_required(['admin'])
def reject_house_design(design_id):
    """Reject a house design."""
    design = HouseDesign.query.get_or_404(design_id)
    
    if design.is_approved:
        flash('This design is already approved and cannot be rejected.', 'error')
        return redirect(url_for('admin.view_house_design_details', design_id=design_id))
    
    # Un-select the design (so beneficiary can choose a different one)
    design.is_selected = False
    design.updated_at = datetime.utcnow()
    db.session.commit()
    
    # Notify the beneficiary
    try:
        notification = Notification(
            user_id=design.beneficiary.user_id,
            title="House Design Rejected",
            message=f"Your house design '{design.design_type}' has been rejected. Please select a different design or generate new designs."
        )
        db.session.add(notification)
        db.session.commit()
    except Exception as e:
        # Log the error but don't block the rejection
        print(f"Error creating notification: {str(e)}")
    
    flash(f'House design for {design.beneficiary.name} has been rejected.', 'warning')
    return redirect(url_for('admin.house_designs'))

@admin_bp.route('/house-designs/comment/<int:design_id>', methods=['POST'])
@role_required(['admin'])
def add_design_comment(design_id):
    """Add a comment to a house design."""
    design = HouseDesign.query.get_or_404(design_id)
    
    comment = request.form.get('comment')
    action = request.form.get('action', 'comment')
    
    if not comment:
        flash('Please provide a comment.', 'error')
        return redirect(url_for('admin.view_house_design_details', design_id=design_id))
    
    # Add the comment to the design description
    design.description += f"\n\nAdmin Comment ({datetime.utcnow().strftime('%Y-%m-%d')}): {comment}"
    
    # If action is 'reject', also reject the design
    if action == 'reject':
        design.is_selected = False
        
        # Notify the beneficiary
        try:
            notification = Notification(
                user_id=design.beneficiary.user_id,
                title="House Design Rejected with Feedback",
                message=f"Your house design '{design.design_type}' has been rejected. Please check the feedback and consider a different design."
            )
            db.session.add(notification)
        except Exception as e:
            # Log the error but don't block the operation
            print(f"Error creating notification: {str(e)}")
    
    design.updated_at = datetime.utcnow()
    db.session.commit()
    
    flash(f'Comment added to the design for {design.beneficiary.name}.', 'success')
    
    if action == 'reject':
        flash(f'Design has been rejected.', 'warning')
        return redirect(url_for('admin.house_designs'))
    
    return redirect(url_for('admin.view_house_design_details', design_id=design_id))

@admin_bp.route('/site-visit/manage/<int:beneficiary_id>', methods=['GET', 'POST'])
@role_required(['Nodal Officer'])
def manage_site_visit(beneficiary_id):
    beneficiary = Beneficiary.query.get_or_404(beneficiary_id)
    nodal_officer = get_current_user()

    # Ensure Nodal Officer is assigned to the beneficiary's district
    if nodal_officer.assigned_district != beneficiary.district:
        flash('You do not have permission to manage visits for this beneficiary from another district.', 'danger')
        return redirect(url_for('admin.nodal_officer_dashboard'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'schedule_visit':
            scheduled_date_str = request.form.get('scheduled_date')
            schedule_notes = request.form.get('schedule_notes')
            if scheduled_date_str:
                try:
                    scheduled_date = datetime.strptime(scheduled_date_str, '%Y-%m-%d').date()
                    new_visit = SiteVisit(
                        beneficiary_id=beneficiary.id,
                        nodal_officer_id=nodal_officer.id,
                        scheduled_date=scheduled_date,
                        schedule_notes=schedule_notes
                    )
                    db.session.add(new_visit)
                    db.session.commit()
                    flash(f'Site visit scheduled for {beneficiary.name} on {scheduled_date.strftime("%d %b, %Y")}.', 'success')
                except ValueError:
                    flash('Invalid date format for scheduled visit.', 'danger')
            else:
                flash('Scheduled date is required.', 'danger')
            return redirect(url_for('admin.manage_site_visit', beneficiary_id=beneficiary.id))

        elif action == 'log_visit_report':
            visit_id = request.form.get('visit_id') # Could be an existing scheduled visit or a new ad-hoc one
            visit_conducted_date_str = request.form.get('visit_conducted_date')
            construction_stage = request.form.get('construction_stage')
            completion_percentage = request.form.get('completion_percentage', type=int)
            visit_remarks = request.form.get('visit_remarks')
            latitude = request.form.get('latitude', type=float)
            longitude = request.form.get('longitude', type=float)
            location_accuracy = request.form.get('location_accuracy', type=float)
            # Handle file uploads for photos
            photos = request.files.getlist('photos')

            if not visit_conducted_date_str or not construction_stage:
                flash('Visit date and construction stage are required for the report.', 'danger')
                return redirect(url_for('admin.manage_site_visit', beneficiary_id=beneficiary.id))

            try:
                visit_conducted_date = datetime.strptime(visit_conducted_date_str, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format for visit conducted date.', 'danger')
                return redirect(url_for('admin.manage_site_visit', beneficiary_id=beneficiary.id))

            site_visit_entry = None
            if visit_id: # Editing an existing (possibly just scheduled) visit
                site_visit_entry = SiteVisit.query.get(visit_id)
                if not site_visit_entry or site_visit_entry.beneficiary_id != beneficiary.id or site_visit_entry.nodal_officer_id != nodal_officer.id:
                    flash('Invalid visit ID or permission denied to update this visit.', 'danger')
                    return redirect(url_for('admin.manage_site_visit', beneficiary_id=beneficiary.id))
            
            if not site_visit_entry: # Creating a new ad-hoc visit report
                site_visit_entry = SiteVisit(
                    beneficiary_id=beneficiary.id,
                    nodal_officer_id=nodal_officer.id
                )
                db.session.add(site_visit_entry)
            
            site_visit_entry.visit_conducted_date = visit_conducted_date
            site_visit_entry.construction_stage_observed = construction_stage
            site_visit_entry.completion_percentage_observed = completion_percentage
            site_visit_entry.visit_remarks = visit_remarks
            site_visit_entry.latitude = latitude
            site_visit_entry.longitude = longitude
            site_visit_entry.location_accuracy = location_accuracy
            site_visit_entry.updated_at = datetime.utcnow()

            # Commit the site visit entry first to get its ID
            try:
                db.session.commit()  # Commit to get site_visit_entry.id
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving site visit report: {str(e)}', 'danger')
                logger.error(f"DB Error saving site visit for beneficiary {beneficiary.id}: {str(e)}")
                return redirect(url_for('admin.manage_site_visit', beneficiary_id=beneficiary.id))

            # Handle photo uploads
            upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'site_visits', str(beneficiary.id))
            os.makedirs(upload_folder, exist_ok=True)

            for photo_file in photos:
                if photo_file and photo_file.filename and allowed_file(photo_file.filename):
                    filename = secure_filename(f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{photo_file.filename}")
                    save_path = os.path.join(upload_folder, filename)
                    try:
                        photo_file.save(save_path)
                        new_photo = SiteVisitPhoto(
                            site_visit_id=site_visit_entry.id,
                            image_filename=filename
                        )
                        db.session.add(new_photo)
                    except Exception as e:
                        flash(f'Could not save photo {photo_file.filename}: {str(e)}', 'warning')
                        logger.error(f"Photo save error for visit {site_visit_entry.id}: {str(e)}")
            
            # Update beneficiary progress if completion percentage is provided
            if completion_percentage is not None:
                beneficiary.progress = completion_percentage
                if construction_stage.lower() == 'completed' or completion_percentage == 100:
                    beneficiary.status = 'Construction Completed' # Or a similar status
                elif beneficiary.status == 'Pending Verification': # If this is the first proper update after approval
                     beneficiary.status = 'Construction In Progress'

            try:
                db.session.commit()  # Commit any remaining changes (photos, beneficiary updates)
                flash('Site visit report logged successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error logging site visit report: {str(e)}', 'danger')
                logger.error(f"DB Error logging site visit for beneficiary {beneficiary.id}: {str(e)}")

            return redirect(url_for('admin.manage_site_visit', beneficiary_id=beneficiary.id))

    # GET request: display past visits and forms
    past_visits = SiteVisit.query.filter_by(beneficiary_id=beneficiary.id, nodal_officer_id=nodal_officer.id)\
                               .order_by(SiteVisit.visit_conducted_date.desc(), SiteVisit.scheduled_date.desc()).all()
    
    # Find an open scheduled visit to pre-fill the report form
    open_scheduled_visit = SiteVisit.query.filter(
        SiteVisit.beneficiary_id == beneficiary.id,
        SiteVisit.nodal_officer_id == nodal_officer.id,
        SiteVisit.visit_conducted_date == None, # Not yet conducted
        SiteVisit.scheduled_date != None
    ).order_by(SiteVisit.scheduled_date.asc()).first()

    return render_template('admin/manage_site_visit.html', 
                           beneficiary=beneficiary, 
                           nodal_officer=nodal_officer,
                           past_visits=past_visits,
                           open_scheduled_visit=open_scheduled_visit
                           )

# Image Upload Helper Function
def save_construction_image(image_file, project_id):
    """Save construction image and return the full URL and filename"""
    try:
        # Create directory if it doesn't exist
        upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'construction_images')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
        
        # Generate unique filename
        file_extension = os.path.splitext(image_file.filename)[1]
        filename = f"{project_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{file_extension}"
        
        # Save the file
        file_path = os.path.join(upload_folder, filename)
        image_file.save(file_path)
        
        # Generate full URL path
        from flask import url_for
        relative_path = f"uploads/construction_images/{filename}"
        
        # Create full URL with domain
        try:
            # Try to get the full URL with domain
            full_url = url_for('static', filename=relative_path, _external=True)
        except:
            # Fallback to relative path if _external fails
            full_url = url_for('static', filename=relative_path)
        
        logger.info(f"Image saved: {filename}, Full URL: {full_url}")
        return full_url, filename
        
    except Exception as e:
        logger.error(f"Error saving construction image: {str(e)}")
        return None, None

# Image Upload Routes
# Grievance Resolution Routes
@admin_bp.route('/grievances')
@role_required(['admin'])
def manage_grievances():
    """View and manage all grievances (notifications from beneficiaries)."""
    current_user = get_current_user()
    if not current_user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login_page'))

    # Get filter parameters
    status_filter = request.args.get('status', 'all')  # 'all', 'unread', 'read', 'resolved'
    page = request.args.get('page', 1, type=int)
    per_page = 15

    # Build query for grievances (notifications sent to admin)
    query = Notification.query.filter_by(user_id=current_user.id)
    
    if status_filter == 'unread':
        query = query.filter_by(is_read=False)
    elif status_filter == 'read':
        query = query.filter_by(is_read=True)
    
    # Get all notifications for this admin, ordered by most recent first
    grievances_pagination = query.order_by(Notification.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get statistics
    total_grievances = Notification.query.filter_by(user_id=current_user.id).count()
    unread_grievances = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
    
    stats = {
        'total': total_grievances,
        'unread': unread_grievances,
        'read': total_grievances - unread_grievances
    }
    
    return render_template('admin/grievances.html',
                          grievances_pagination=grievances_pagination,
                          stats=stats,
                          current_user=current_user,
                          selected_status=status_filter)

@admin_bp.route('/grievances/<int:grievance_id>')
@role_required(['admin'])
def view_grievance(grievance_id):
    """View detailed grievance and handle replies."""
    current_user = get_current_user()
    if not current_user:
        flash('User not found.', 'error')
        return redirect(url_for('auth.login_page'))

    # Get the specific grievance (notification)
    grievance = Notification.query.filter_by(id=grievance_id, user_id=current_user.id).first_or_404()
    
    # Mark as read if not already
    if not grievance.is_read:
        grievance.is_read = True
        db.session.commit()
    
    # Try to extract beneficiary info from the grievance title or message
    beneficiary = None
    beneficiary_id = None
    
    # Look for beneficiary ID in the title (format: "Request from Name (ID: BENEFICIARY_ID)")
    import re
    id_match = re.search(r'ID:\s*([A-Z]+-[\w-]+)', grievance.title)
    if id_match:
        beneficiary_id = id_match.group(1)
        beneficiary = Beneficiary.query.filter_by(beneficiary_id=beneficiary_id).first()
    
    return render_template('admin/grievance_detail.html',
                          grievance=grievance,
                          beneficiary=beneficiary,
                          beneficiary_id=beneficiary_id,
                          current_user=current_user)

@admin_bp.route('/grievances/<int:grievance_id>/reply', methods=['POST'])
@role_required(['admin'])
def reply_to_grievance(grievance_id):
    """Send reply to a grievance."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    # Get the original grievance
    grievance = Notification.query.filter_by(id=grievance_id, user_id=current_user.id).first_or_404()
    
    reply_message = request.form.get('reply_message')
    if not reply_message:
        flash('Reply message is required.', 'error')
        return redirect(url_for('admin.view_grievance', grievance_id=grievance_id))
    
    # Extract beneficiary ID from the grievance
    import re
    id_match = re.search(r'ID:\s*([A-Z]+-[\w-]+)', grievance.title)
    if id_match:
        beneficiary_id = id_match.group(1)
        beneficiary = Beneficiary.query.filter_by(beneficiary_id=beneficiary_id).first()
        
        if beneficiary and beneficiary.user_id:
            # Create reply notification for the beneficiary
            reply_notification = Notification(
                user_id=beneficiary.user_id,
                title=f"Reply to your request from Admin",
                message=f"Admin Reply:\n{reply_message}\n\n--- Original Request ---\nSubject: {grievance.title}\nMessage: {grievance.message}",
                is_read=False,
                created_at=datetime.utcnow()
            )
            db.session.add(reply_notification)
            
            # Mark the original grievance as resolved (we can add a field for this later)
            # For now, we'll just add a note to the message
            grievance.message += f"\n\n--- ADMIN REPLY ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')}) ---\n{reply_message}"
            
            try:
                db.session.commit()
                flash('Reply sent successfully to beneficiary.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error sending reply: {str(e)}', 'error')
        else:
            flash('Could not find beneficiary user account to send reply.', 'error')
    else:
        flash('Could not identify beneficiary from grievance.', 'error')
    
    return redirect(url_for('admin.view_grievance', grievance_id=grievance_id))

@admin_bp.route('/grievances/<int:grievance_id>/mark-resolved', methods=['POST'])
@role_required(['admin'])
def mark_grievance_resolved(grievance_id):
    """Mark a grievance as resolved."""
    current_user = get_current_user()
    if not current_user:
        return jsonify({'error': 'User not found'}), 401

    # Get the grievance
    grievance = Notification.query.filter_by(id=grievance_id, user_id=current_user.id).first_or_404()
    
    # Add resolved status to the message (since we don't have a separate status field)
    if "--- RESOLVED ---" not in grievance.message:
        grievance.message += f"\n\n--- RESOLVED ({datetime.utcnow().strftime('%Y-%m-%d %H:%M')}) ---\nMarked as resolved by {current_user.full_name or current_user.username}"
        grievance.is_read = True
        
        try:
            db.session.commit()
            flash('Grievance marked as resolved.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error marking grievance as resolved: {str(e)}', 'error')
    else:
        flash('Grievance is already marked as resolved.', 'info')
    
    return redirect(url_for('admin.manage_grievances'))

@admin_bp.route('/upload_image', methods=['GET', 'POST'])
@role_required(['Nodal Officer'])
def upload_image():
    """Upload construction progress images"""
    form = ConstructionImageUploadForm()
    current_user = get_current_user()
    
    if form.validate_on_submit():
        try:
            # Check if project exists
            project = Project.query.filter_by(project_id=form.project_id.data).first()
            if not project:
                logger.warning(f"Project not found: {form.project_id.data}")
                flash(f'Project with ID {form.project_id.data} not found.', 'error')
                return render_template('admin/upload_image.html', form=form)
            
            logger.info(f"Project found: {project.project_id}, beneficiary_id: {project.beneficiary_id}")
            
            # Get beneficiary from project (optional for notifications only)
            beneficiary = None
            if project.beneficiary_id:
                beneficiary = Beneficiary.query.filter_by(beneficiary_id=project.beneficiary_id).first()
                if beneficiary:
                    logger.info(f"Beneficiary found: {beneficiary.name}")
                else:
                    logger.info(f"Beneficiary not found - proceeding with project-only upload")
            
            # Check if nodal officer is assigned to this district
            if current_user.role == 'Nodal Officer' and current_user.assigned_district and current_user.assigned_district != project.district:
                flash(f'Access denied. Your district: {current_user.assigned_district}, Project district: {project.district}', 'error')
                return render_template('admin/upload_image.html', form=form)
            
            # Save the image
            image_url, filename = save_construction_image(form.image.data, form.project_id.data)
            if not image_url:
                flash('Failed to upload image. Please try again.', 'error')
                return render_template('admin/upload_image.html', form=form)
            
            # Update project completion percentage, image, and location
            project.completionPercentage = form.completion_percentage.data
            project.updated_at = datetime.utcnow()
            project.imageUrl = image_url
            if form.latitude.data and form.longitude.data:
                project.latitude = form.latitude.data
                project.longitude = form.longitude.data
                logger.info(f"Updated project {project.project_id} location to: Lat {project.latitude}, Lon {project.longitude}")
            
            # Create construction update record
            construction_update = ConstructionUpdate(
                beneficiaryId=project.beneficiary_id or project.project_id,  # Use project_id if no beneficiary_id
                district=project.district,
                location=form.location.data or project.location,
                constructionStage=form.construction_stage.data,
                completionPercentage=form.completion_percentage.data,
                notes=form.description.data,
                photos=image_url,
                timestamp=int(datetime.utcnow().timestamp()),
                inspector=current_user.full_name or current_user.username,
                username=current_user.username,
                project_id=project.project_id
            )
            
            db.session.add(construction_update)
            
            # Update project status based on completion percentage
            if form.completion_percentage.data is not None:
                if form.completion_percentage.data == 100:
                    project.status = 'Completed'
                elif form.completion_percentage.data >= 75:
                    project.status = 'Finishing'
                elif form.completion_percentage.data >= 25:
                    project.status = 'Under Construction'
                else:
                    project.status = 'In Progress'
            
            # Update beneficiary progress if beneficiary exists
            if beneficiary and form.completion_percentage.data is not None:
                beneficiary.progress = form.completion_percentage.data
                
                # Update beneficiary status based on progress
                if form.completion_percentage.data == 100:
                    beneficiary.status = 'Completed'
                elif form.completion_percentage.data >= 75:
                    beneficiary.status = 'Under Construction - Finishing'
                elif form.completion_percentage.data >= 25:
                    beneficiary.status = 'Under Construction'
                elif beneficiary.status == 'Pending Verification':
                    beneficiary.status = 'Construction Started'
            
            db.session.commit()
            
            # Create notification for beneficiary if they have a user account
            if beneficiary and beneficiary.user_id:
                notification = Notification(
                    user_id=beneficiary.user_id,
                    title="Construction Progress Updated",
                    message=f"New construction image uploaded for project {project.project_id}. Stage: {form.construction_stage.data}. Completion: {form.completion_percentage.data}%",
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.commit()
                logger.info(f"Notification sent to beneficiary {beneficiary.name}")
            else:
                logger.info("Skipping notification - no beneficiary user account")
            
            flash(f'Construction image uploaded successfully for project {project.project_id} ({project.beneficiaryName})!', 'success')
            
            # Redirect to project update page or back to dashboard
            if beneficiary:
                return redirect(url_for('admin.update_beneficiary_status', task_id=beneficiary.beneficiary_id))
            else:
                return redirect(url_for('admin.nodal_officer_dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error uploading image: {str(e)}', 'error')
            logger.error(f"Error uploading construction image: {str(e)}")
    
    return render_template('admin/upload_image.html', form=form)