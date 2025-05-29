from flask import render_template, request, redirect, url_for, flash, jsonify, session
from . import beneficiary_bp
from functools import wraps
from app import db # Add db import
from models import User, Project, Beneficiary, ConstructionUpdate, Notification, PlotImage, HouseDesign # Add model imports
from werkzeug.utils import secure_filename # For document uploads
import os # For document uploads
from flask import current_app # To get app config for uploads
from .forms import BeneficiaryProfileForm, DocumentUploadForm, UpdateRequestForm, PlotImageUploadForm, HouseDesignSelectionForm, HouseDesignFinalizationForm # Add form imports
from .ai_architect import AIArchitectService # Import AI Architect service
import uuid
from datetime import datetime
from app import DISTRICTS, BLOCKS_BY_DISTRICT

# Decorator for beneficiary access check
def beneficiary_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Please log in to access this page.', 'info')
            return redirect(url_for('auth.login_page'))

        user = User.query.get(user_id)
        if not user:
            flash('User not found. Please log in again.', 'error')
            session.clear()
            return redirect(url_for('auth.login_page'))

        # Check if the user has an associated beneficiary profile
        beneficiary = Beneficiary.query.filter_by(user_id=user.id).first()
        if not beneficiary:
            # If user has 'beneficiary' role but no direct link, this is an inconsistency.
            # For now, we deny access. Consider creating a profile or specific error.
            if user.role.lower() == 'beneficiary':
                flash('Beneficiary profile not found. Please contact support.', 'error')
            else:
                flash('You do not have access to this beneficiary section.', 'error')
            return redirect(url_for('index'))
        
        # Add beneficiary to kwargs to be accessible in the route
        new_kwargs = kwargs.copy()
        new_kwargs['beneficiary'] = beneficiary
        return f(*args, **new_kwargs)
    return decorated_function

# Helper to get current beneficiary profile
def get_current_beneficiary_profile():
    user_id = session.get('user_id')
    if not user_id:
        return None
    
    # Fetch user, then their linked beneficiary profile
    user = User.query.get(user_id)
    if not user:
        return None
    
    return Beneficiary.query.filter_by(user_id=user.id).first()

# Dashboard for beneficiaries
@beneficiary_bp.route('/')
@beneficiary_bp.route('/dashboard')
@beneficiary_required
def dashboard(beneficiary):
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))

    # Get the user's project (assuming one project per beneficiary)
    project = Project.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).first()
    if not project:
        return render_template('beneficiary/dashboard.html', project=None)

    # Fetch ConstructionUpdate records for this beneficiary
    updates = ConstructionUpdate.query.filter_by(beneficiaryId=beneficiary.beneficiary_id).order_by(ConstructionUpdate.update_date).all()

    payments = []
    stages = []
    funds_utilized = []
    completion_per_stage = []
    daily_updates = []
    after_img = None

    for upd in updates:
        payments.append({
            "stage": upd.constructionStage,
            "sanctioned": getattr(upd, "payment_sanctioned", 0),  # If you have this field
            "used": getattr(upd, "payment_used", 0),              # If you have this field
            "status": getattr(upd, "payment_status", "Unknown") # If you have this field
        })
        stages.append(upd.constructionStage)
        funds_utilized.append(getattr(upd, "payment_used", 0))
        completion_per_stage.append(upd.completionPercentage)
        daily_updates.append({
            "date": upd.update_date.strftime('%Y-%m-%d'),
            "stage": upd.constructionStage,
            "notes": upd.notes,
            "completion": upd.completionPercentage,
            "after_img": upd.photos.split(',')[0] if upd.photos else None
        })
    if daily_updates:
        after_img = daily_updates[-1]["after_img"]

    before_img = getattr(project, 'ai_architect_image_url', None)

    return render_template(
        'beneficiary/dashboard.html',
        project=project,
        payments=payments,
        daily_updates=daily_updates,
        before_img=before_img,
        after_img=after_img,
        stages=stages,
        funds_utilized=funds_utilized,
        completion_per_stage=completion_per_stage,
        beneficiary=beneficiary
    )

# Profile page for beneficiaries
@beneficiary_bp.route('/profile', methods=['GET', 'POST'])
@beneficiary_required
def profile(beneficiary):
    """Profile page for beneficiary to update personal information."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        try:
            # Update beneficiary details from form
            beneficiary.name = request.form.get('name', beneficiary.name)
            beneficiary.contactNumber = request.form.get('contactNumber', beneficiary.contactNumber)
            beneficiary.address = request.form.get('address', beneficiary.address)
            
            # Email is on the User model, update user.email instead
            if beneficiary.user:
                beneficiary.user.email = request.form.get('email', beneficiary.user.email)
            
            # Add other updatable fields as necessary
            db.session.commit()
            flash('Profile updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating profile: {str(e)}', 'error')
        
        return redirect(url_for('beneficiary.profile'))
    
    return render_template('beneficiary/profile.html', beneficiary=beneficiary)

# Project progress for beneficiaries
@beneficiary_bp.route('/project/<project_id_str>') # Use a dynamic segment for project_id
@beneficiary_required
def project(beneficiary, project_id_str):
    """Show project details and construction progress for a specific project."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))

    # Fetch the specific project ensuring it belongs to this beneficiary
    project_instance = Project.query.filter_by(project_id=project_id_str, beneficiary_id=beneficiary.beneficiary_id).first_or_404()
    
    # Fetch construction updates for this project
    updates = ConstructionUpdate.query.filter_by(project_id=project_instance.project_id).order_by(ConstructionUpdate.update_date.desc()).all()
    
    return render_template('beneficiary/project.html', project=project_instance, updates=updates, beneficiary=beneficiary)


# Update request submission (e.g. reporting an issue or asking a question)
@beneficiary_bp.route('/request-update', methods=['GET', 'POST'])
@beneficiary_required
def request_update(beneficiary):
    """Submit requests for updates or issues with housing project."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        subject = request.form.get('subject')
        message_text = request.form.get('message')
        project_id = request.form.get('project_id') # If request is project-specific

        if not subject or not message_text:
            flash('Subject and message are required.', 'error')
        else:
            # This could create a Notification for admin, or a new model e.g., SupportTicket
            # Example: Creating a notification for admin (ensure admin user_id or a generic way to flag for admin)
            # Find admin users (case-insensitive search for 'admin' role)
            admin_users = User.query.filter(User.role.ilike('%admin%')).all()
            
            if admin_users:
                for admin_user in admin_users: # Notify all admins, or pick one
                    notif_title = f"Request from {beneficiary.name} (ID: {beneficiary.beneficiary_id})"
                    if project_id:
                        notif_title += f" regarding Project {project_id}"
                    
                    new_notification = Notification(
                        user_id=admin_user.id, 
                        title=notif_title,
                        message=f"Subject: {subject}\n\n{message_text}",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(new_notification)
                db.session.commit()
                flash('Your request has been submitted successfully.', 'success')
            else:
                flash('Could not find an admin to send the request to. Please contact support.', 'error')
            return redirect(url_for('beneficiary.dashboard'))
    
    projects = Project.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).all()
    return render_template('beneficiary/request_update.html', beneficiary=beneficiary, projects=projects)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

# Document submission
@beneficiary_bp.route('/documents', methods=['GET', 'POST'])
@beneficiary_required
def documents(beneficiary):
    """Upload and manage required documents."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'document' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
        file = request.files['document']
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        document_type = request.form.get('document_type') # e.g., 'income_certificate', 'voter_id'

        if file and allowed_file(file.filename) and document_type:
            filename = secure_filename(file.filename)
            # Ensure upload folder for the specific beneficiary exists or is handled correctly
            # Example: static/uploads/beneficiary_ID/filename
            beneficiary_upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'beneficiary', str(beneficiary.beneficiary_id))
            if not os.path.exists(beneficiary_upload_folder):
                os.makedirs(beneficiary_upload_folder)
            
            file_path = os.path.join(beneficiary_upload_folder, filename)
            file.save(file_path)
            
            # Update beneficiary model with the path to the document
            if document_type == 'income_certificate':
                beneficiary.income_certificate_filename = os.path.join('beneficiary', str(beneficiary.beneficiary_id), filename) # Store relative path
            elif document_type == 'photo':
                 beneficiary.photo_url = os.path.join('beneficiary', str(beneficiary.beneficiary_id), filename)
            # Add other document types as fields in Beneficiary model
            
            db.session.commit()
            flash(f'{document_type.replace("_", " ").title()} uploaded successfully.', 'success')
        else:
            flash('File type not allowed or document type not specified.', 'error')
        return redirect(url_for('beneficiary.documents'))
    
    # Pass existing documents to template if stored on model
    return render_template('beneficiary/documents.html', beneficiary=beneficiary)

# API endpoint for project updates (specific to a beneficiary)
@beneficiary_bp.route('/api/project-updates')
@beneficiary_required
def api_project_updates(beneficiary):
    """Get project updates for the logged-in beneficiary."""
    if not beneficiary:
        return jsonify({'error': 'Beneficiary profile not found'}), 404

    projects = Project.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).all()
    updates_data = []
    for proj in projects:
        construction_updates = ConstructionUpdate.query.filter_by(project_id=proj.project_id).order_by(ConstructionUpdate.update_date.desc()).all()
        project_updates_info = {
            'project_id': proj.project_id,
            'project_name': proj.beneficiaryName, # Or a specific project name field
            'status': proj.status,
            'completionPercentage': proj.completionPercentage,
            'updates': [
                {
                    'date': upd.update_date.strftime('%Y-%m-%d'),
                    'stage': upd.constructionStage,
                    'status': 'Completed' if upd.completionPercentage == 100 else 'In Progress', # Simplified status
                    'notes': upd.notes,
                    'photos': upd.photos.split(',') if upd.photos else [] # Assuming comma-separated photo URLs
                } for upd in construction_updates
            ]
        }
        updates_data.append(project_updates_info)

    return jsonify({'success': True, 'data': updates_data})

# ---- AI Architect Feature Routes ----

@beneficiary_bp.route('/ai-architect')
@beneficiary_required
def ai_architect_dashboard(beneficiary):
    """AI Architect dashboard for beneficiaries."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))
    
    # Get latest plot image if exists
    latest_plot_image = PlotImage.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).order_by(PlotImage.created_at.desc()).first()
    
    # Get house designs for this beneficiary
    designs = HouseDesign.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).all()
    
    # Get selected design if exists
    selected_design = HouseDesign.query.filter_by(beneficiary_id=beneficiary.beneficiary_id, is_selected=True).first()
    
    upload_form = PlotImageUploadForm()
    
    return render_template('beneficiary/ai_architect_dashboard.html', 
                          beneficiary=beneficiary,
                          plot_image=latest_plot_image,
                          designs=designs,
                          selected_design=selected_design,
                          upload_form=upload_form)

@beneficiary_bp.route('/ai-architect/upload-plot', methods=['GET', 'POST'])
@beneficiary_required
def upload_plot_image(beneficiary):
    """Upload a plot image for AI house design generation."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))
    
    form = PlotImageUploadForm()
    
    if form.validate_on_submit():
        # Save the uploaded plot image
        plot_image = form.plot_image.data
        if plot_image and allowed_file(plot_image.filename):
            filename = secure_filename(plot_image.filename)
            plot_image_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'plot_images', beneficiary.beneficiary_id)
            
            # Create directory if it doesn't exist
            if not os.path.exists(plot_image_folder):
                os.makedirs(plot_image_folder)
            
            # Save the image
            file_path = os.path.join(plot_image_folder, filename)
            plot_image.save(file_path)
            
            # Create PlotImage record in the database
            relative_path = os.path.join('plot_images', beneficiary.beneficiary_id, filename)
            new_plot_image = PlotImage(
                beneficiary_id=beneficiary.beneficiary_id,
                image_url=relative_path
            )
            db.session.add(new_plot_image)
            db.session.commit()
            
            # Generate designs using AI Architect
            return redirect(url_for('beneficiary.generate_designs', plot_image_id=new_plot_image.id))
        else:
            flash('Invalid file format. Please upload a valid image.', 'error')
    
    return render_template('beneficiary/upload_plot.html', form=form, beneficiary=beneficiary)

@beneficiary_bp.route('/ai-architect/generate-designs/<int:plot_image_id>')
@beneficiary_required
def generate_designs(beneficiary, plot_image_id):
    """Generate house designs using AI based on uploaded plot image."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))
    
    # Get the plot image
    plot_image = PlotImage.query.get_or_404(plot_image_id)
    if plot_image.beneficiary_id != beneficiary.beneficiary_id:
        flash('You do not have permission to access this resource.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Initialize AI Architect service
        ai_architect = AIArchitectService()
        
        # Get full path of the image
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], plot_image.image_url)
        
        # Generate designs
        designs = ai_architect.generate_designs(
            plot_image_path=image_path,
            beneficiary=beneficiary,
            fund_allocation=beneficiary.allocated_fund,
            additional_info=None
        )
        
        # Save designs to database
        for design_data in designs:
            new_design = HouseDesign(
                beneficiary_id=beneficiary.beneficiary_id,
                plot_image_id=plot_image.id,
                design_type=design_data['design_type'],
                image_url=design_data['image_url'],
                building_cost=design_data['building_cost'],
                labor_cost=design_data['labor_cost'],
                total_cost=design_data['total_cost'],
                description=design_data['description']
            )
            db.session.add(new_design)
        
        db.session.commit()
        flash('House designs generated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error generating house designs: {str(e)}', 'error')
    
    return redirect(url_for('beneficiary.view_designs', plot_image_id=plot_image_id))

@beneficiary_bp.route('/ai-architect/view-designs/<int:plot_image_id>')
@beneficiary_required
def view_designs(beneficiary, plot_image_id):
    """View AI-generated house designs for a specific plot image."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))
    
    # Get the plot image
    plot_image = PlotImage.query.get_or_404(plot_image_id)
    if plot_image.beneficiary_id != beneficiary.beneficiary_id:
        flash('You do not have permission to access this resource.', 'error')
        return redirect(url_for('index'))
    
    # Get designs for this plot image
    designs = HouseDesign.query.filter_by(plot_image_id=plot_image_id).all()
    
    # If no designs found, redirect to generate designs
    if not designs:
        return redirect(url_for('beneficiary.generate_designs', plot_image_id=plot_image_id))
    
    # Create selection form
    form = HouseDesignSelectionForm()
    form.design_id.choices = [(design.id, design.design_type) for design in designs]
    
    return render_template('beneficiary/view_designs.html', 
                          beneficiary=beneficiary,
                          plot_image=plot_image,
                          designs=designs,
                          form=form)

@beneficiary_bp.route('/ai-architect/select-design/<int:plot_image_id>', methods=['POST'])
@beneficiary_required
def select_design(beneficiary, plot_image_id):
    """Select one of the four generated house designs."""
    if not beneficiary:
        # flash('Beneficiary profile not found.', 'error') # For API, jsonify is better
        return jsonify({"success": False, "message": "Beneficiary profile not found."}), 404
    
    form = HouseDesignSelectionForm()
    form.design_id.choices = [(design.id, design.design_type) for design in 
                              HouseDesign.query.filter_by(plot_image_id=plot_image_id).all()]
    
    if form.validate_on_submit():
        design_id = form.design_id.data
        comments = form.comments.data
        
        # Get the selected design
        selected_design = HouseDesign.query.get_or_404(design_id)
        if selected_design.beneficiary_id != beneficiary.beneficiary_id:
            flash('You do not have permission to access this resource.', 'error')
            return redirect(url_for('index'))
        
        # Unselect any previously selected designs
        HouseDesign.query.filter_by(beneficiary_id=beneficiary.beneficiary_id, is_selected=True).update({'is_selected': False})
        
        # Mark this design as selected
        selected_design.is_selected = True
        db.session.commit()
        
        # Save any comments provided
        if comments:
            selected_design.description += f"\n\nUser comments: {comments}"
            db.session.commit()
        
        # Generate detailed design (interiors, exteriors, blueprints)
        return redirect(url_for('beneficiary.generate_detailed_design', design_id=design_id))
    
    flash('Please select a design.', 'error')
    return redirect(url_for('beneficiary.view_designs', plot_image_id=plot_image_id))

@beneficiary_bp.route('/ai-architect/detailed-design/<int:design_id>')
@beneficiary_required
def generate_detailed_design(beneficiary, design_id):
    """Generate detailed interior/exterior views and blueprints for the selected design."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))
    
    # Get the selected design
    design = HouseDesign.query.get_or_404(design_id)
    if design.beneficiary_id != beneficiary.beneficiary_id:
        flash('You do not have permission to access this resource.', 'error')
        return redirect(url_for('index'))
    
    try:
        # Initialize AI Architect service
        ai_architect = AIArchitectService()
        
        # Generate detailed designs
        detailed_design = ai_architect.generate_detailed_design(
            design_id=design.id,
            original_design_data=design,
            comments=None
        )
        
        # Update the design with detailed views
        design.interior_url = detailed_design['interior_url']
        design.exterior_url = detailed_design['exterior_url']
        design.blueprint_url = detailed_design['blueprint_url']
        design.description = detailed_design['description']
        
        db.session.commit()
        flash('Detailed design generated successfully!', 'success')
        
    except Exception as e:
        flash(f'Error generating detailed design: {str(e)}', 'error')
    
    return redirect(url_for('beneficiary.review_detailed_design', design_id=design_id))

@beneficiary_bp.route('/ai-architect/review-design/<int:design_id>', methods=['GET', 'POST'])
@beneficiary_required
def review_detailed_design(beneficiary, design_id):
    """Review and confirm the detailed design before submission."""
    if not beneficiary:
        flash('Beneficiary profile not found.', 'error')
        return redirect(url_for('index'))
    
    # Get the selected design
    design = HouseDesign.query.get_or_404(design_id)
    if design.beneficiary_id != beneficiary.beneficiary_id:
        flash('You do not have permission to access this resource.', 'error')
        return redirect(url_for('index'))
    
    form = HouseDesignFinalizationForm()
    
    if form.validate_on_submit():
        if form.confirm.data == 'yes':
            # Submit design for admin approval
            design.is_approved = False  # Needs admin approval
            
            # Add any final comments
            if form.final_comments.data:
                design.description += f"\n\nFinal comments: {form.final_comments.data}"
            
            db.session.commit()
            
            # Notify admin about new design submission
            admin_users = User.query.filter(User.role.ilike('%admin%')).all()
            for admin_user in admin_users:
                notification = Notification(
                    user_id=admin_user.id,
                    title=f"New House Design Submitted by {beneficiary.name}",
                    message=f"Beneficiary {beneficiary.name} (ID: {beneficiary.beneficiary_id}) has submitted a house design for approval. Please review it.",
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
            
            db.session.commit()
            
            flash('Your house design has been submitted for approval!', 'success')
            return redirect(url_for('beneficiary.ai_architect_dashboard'))
        
        else:
            # User wants more changes
            return redirect(url_for('beneficiary.generate_detailed_design', design_id=design_id))
    
    return render_template('beneficiary/review_design.html', 
                          beneficiary=beneficiary,
                          design=design,
                          form=form)

# Application route for logged-in beneficiaries to apply for housing
@beneficiary_bp.route('/apply-for-housing', methods=['GET', 'POST'])
@beneficiary_required
def apply_for_housing(beneficiary):
    """Allow logged-in beneficiaries to apply for housing scheme"""
    
    # Check if there's already a pending application
    if beneficiary.status not in ['Rejected', None]:
        flash('You already have an active application in progress.', 'info')
        return redirect(url_for('beneficiary.dashboard'))
    
    if request.method == 'POST':
        # Generate a unique application ID
        timestamp_part = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = str(uuid.uuid4()).replace('-', '')[:8]
        application_id = f"SGAY-{timestamp_part}-{random_part}"
        
        # Update beneficiary information from form
        beneficiary.beneficiary_id = application_id
        beneficiary.name = request.form.get('name', beneficiary.name)
        beneficiary.district = request.form.get('district')
        beneficiary.block = request.form.get('block')
        beneficiary.village = request.form.get('village')
        beneficiary.address = request.form.get('address')
        beneficiary.contactNumber = request.form.get('contactNumber')
        beneficiary.aadhar_number = request.form.get('aadhar_number')
        beneficiary.annual_income = request.form.get('annual_income')
        beneficiary.family_members = request.form.get('family_members')
        beneficiary.housing_status = request.form.get('housing_status')
        beneficiary.gender = request.form.get('gender')
        beneficiary.category = request.form.get('category')
        beneficiary.scheme = request.form.get('scheme', 'sgay')
        beneficiary.status = 'Applied'
        beneficiary.progress = 5
        beneficiary.applicationDate = datetime.utcnow().strftime('%Y-%m-%d')
        
        # Save changes to database
        try:
            db.session.commit()
            
            # Notify admin about new application
            admin_users = User.query.filter(User.role.ilike('%admin%')).all()
            if admin_users:
                for admin in admin_users:
                    notification = Notification(
                        user_id=admin.id,
                        title="New Housing Application",
                        message=f"A new housing application has been submitted by {beneficiary.name} (ID: {application_id})",
                        is_read=False,
                        created_at=datetime.utcnow()
                    )
                    db.session.add(notification)
                db.session.commit()
            
            # Create a notification for the beneficiary as well
            if beneficiary.user_id:
                notification = Notification(
                    user_id=beneficiary.user_id,
                    title="Application Submitted Successfully",
                    message=f"Your housing application (ID: {application_id}) has been submitted successfully. We will review it shortly.",
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
                db.session.commit()
            
            flash(f'Housing application submitted successfully! Your Application ID is: {application_id}', 'success')
            return redirect(url_for('beneficiary.application_status'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error saving application: {str(e)}', 'error')
    
    return render_template('beneficiary/apply_housing.html', 
                          beneficiary=beneficiary,
                          districts=DISTRICTS,
                          blocks_by_district=BLOCKS_BY_DISTRICT)

@beneficiary_bp.route('/application-status')
@beneficiary_required
def application_status(beneficiary):
    """View status of housing application and updates"""
    if not beneficiary.beneficiary_id:
        flash('You have not applied for housing yet.', 'info')
        return redirect(url_for('beneficiary.apply_for_housing'))
    
    # Get all updates and activities related to this application
    updates = []
    
    # If there's a linked project, get construction updates
    project = Project.query.filter_by(beneficiary_id=beneficiary.beneficiary_id).first()
    if project:
        construction_updates = ConstructionUpdate.query.filter_by(
            beneficiaryId=beneficiary.beneficiary_id
        ).order_by(ConstructionUpdate.update_date.desc()).all()
        
        for update in construction_updates:
            updates.append({
                'date': update.update_date,
                'title': f"Construction Update: {update.constructionStage}",
                'message': update.notes,
                'status': 'construction',
                'completion': update.completionPercentage,
                'image': update.photos.split(',')[0] if update.photos else None
            })
    
    # Add application status milestones
    if beneficiary.applicationDate:
        updates.append({
            'date': datetime.strptime(beneficiary.applicationDate, '%Y-%m-%d'),
            'title': 'Application Submitted',
            'message': 'Your housing application has been received.',
            'status': 'submitted',
            'completion': 5
        })
    
    if beneficiary.status == 'Pending Verification' and beneficiary.approvalDate:
        updates.append({
            'date': datetime.strptime(beneficiary.approvalDate, '%Y-%m-%d'),
            'title': 'Application Approved by Admin',
            'message': 'Your application has been approved and is pending verification by a Nodal Officer.',
            'status': 'approved',
            'completion': 20
        })
    
    if beneficiary.status == 'Verified':
        updates.append({
            'date': datetime.strptime(beneficiary.approvalDate, '%Y-%m-%d') if beneficiary.approvalDate else datetime.utcnow(),
            'title': 'Application Verified by Nodal Officer',
            'message': 'Your application has been verified. Project allocation will begin soon.',
            'status': 'verified',
            'completion': 40
        })
    
    # Sort updates by date, most recent first
    updates.sort(key=lambda x: x['date'], reverse=True)
    
    return render_template('beneficiary/application_status.html', 
                          beneficiary=beneficiary,
                          updates=updates,
                          project=project)

# Add a route to find applications by ID for users who have submitted but can't see their application
@beneficiary_bp.route('/find-application', methods=['GET', 'POST'])
def find_application():
    """Allow users to search for their existing application by ID"""
    
    if request.method == 'POST':
        application_id = request.form.get('application_id')
        if not application_id:
            flash('Please enter an application ID.', 'error')
            return render_template('beneficiary/find_application.html')
        
        # Find the application
        beneficiary = Beneficiary.query.filter_by(beneficiary_id=application_id).first()
        
        if not beneficiary:
            flash('Application not found. Please check the ID and try again.', 'error')
            return render_template('beneficiary/find_application.html')
        
        # Check if this application is already linked to a user
        if beneficiary.user_id:
            user = User.query.get(beneficiary.user_id)
            if user:
                flash(f'This application is already linked to user {user.username}. Please login to view it.', 'info')
                return redirect(url_for('auth.login_page'))
        
        # If we're here, the application exists but isn't linked to a user account
        # If user is logged in, associate the application with their account
        user_id = session.get('user_id')
        if user_id:
            user = User.query.get(user_id)
            if user:
                # Link the application to this user
                beneficiary.user_id = user_id
                db.session.commit()
                flash(f'Application found and linked to your account! (ID: {application_id})', 'success')
                return redirect(url_for('beneficiary.application_status'))
        
        # If user is not logged in, prompt them to create an account
        session['temp_application_id'] = application_id
        flash(f'Application found (ID: {application_id})! Please create an account or login to view it.', 'success')
        return redirect(url_for('auth.register_page'))
    
    return render_template('beneficiary/find_application.html') 