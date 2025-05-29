from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(16), default='beneficiary')  # 'admin', 'nodal_officer', or 'beneficiary'
    full_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    phone_number = db.Column(db.String(15), unique=True, nullable=True)  # For OTP login
    otp = db.Column(db.String(6), nullable=True)  # For storing temporary OTP
    otp_generated_at = db.Column(db.DateTime, nullable=True)  # For OTP expiry
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    assigned_district = db.Column(db.String(100), nullable=True)  # For Nodal Officers
    preferred_scheme = db.Column(db.String(10), nullable=True)  # 'pmay' or 'sgay'
    login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    beneficiaries = db.relationship('Beneficiary', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Beneficiary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(db.String(32), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    block = db.Column(db.String(100), nullable=True)
    village = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(32), nullable=False)
    progress = db.Column(db.Integer, nullable=False)
    contactNumber = db.Column(db.String(32), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    applicationDate = db.Column(db.String(32), nullable=True)
    approvalDate = db.Column(db.String(32), nullable=True)
    annual_income = db.Column(db.Integer, nullable=True)
    family_members = db.Column(db.Integer, nullable=True)
    aadhar_number = db.Column(db.String(20), nullable=True)
    photo_url = db.Column(db.String(200), nullable=True)
    occupation = db.Column(db.String(50), nullable=True)
    housing_status = db.Column(db.String(50), nullable=True)
    income_certificate_filename = db.Column(db.String(255), nullable=True)
    voter_id = db.Column(db.String(20), nullable=True)
    ration_card_number = db.Column(db.String(20), nullable=True)
    additional_comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    scheme = db.Column(db.String(10), default='sgay', nullable=True)  # 'pmay' or 'sgay'
    gender = db.Column(db.String(10), nullable=True)
    category = db.Column(db.String(20), nullable=True)  # SC, ST, OBC, General, Minority
    sc_certificate_filename = db.Column(db.String(255), nullable=True) # For SC category certificate
    bank_name = db.Column(db.String(100), nullable=True)
    account_number = db.Column(db.String(50), nullable=True)
    ifsc_code = db.Column(db.String(20), nullable=True)
    land_ownership = db.Column(db.String(20), nullable=True)
    property_area = db.Column(db.Integer, nullable=True)
    pmay_component = db.Column(db.String(10), nullable=True)  # BLC, CLSS, AHP, ISSR
    allocated_fund = db.Column(db.Float, nullable=True)  # Fund allocated for house construction

    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    projects = db.relationship('Project', backref='beneficiary', lazy=True,
                              primaryjoin="Beneficiary.beneficiary_id==Project.beneficiary_id")
    plot_images = db.relationship('PlotImage', backref='beneficiary', lazy=True,
                                 primaryjoin="Beneficiary.beneficiary_id==PlotImage.beneficiary_id")
    house_designs = db.relationship('HouseDesign', backref='beneficiary', lazy=True,
                                   primaryjoin="Beneficiary.beneficiary_id==HouseDesign.beneficiary_id")
    def __repr__(self):
        return f'<Beneficiary {self.beneficiary_id}>'

class OTP(db.Model):
    """Model for storing temporary OTP codes"""
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.String(20), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

    def __init__(self, application_id, otp_code):
        self.application_id = application_id
        self.otp_code = otp_code
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(minutes=5)  # OTP expires in 5 minutes
        # Print for debugging
        print(f"OTP created for {application_id}: {otp_code}, expires at {self.expires_at}")

    def __repr__(self):
        return f"<OTP {self.otp_code} for {self.application_id}>"

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(32), unique=True, nullable=False)
    beneficiaryName = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(32), nullable=False)
    allocation = db.Column(db.Integer, nullable=False)
    completionPercentage = db.Column(db.Integer, nullable=False)
    startDate = db.Column(db.String(32), nullable=False)
    imageUrl = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    end_date = db.Column(db.String(32), nullable=True)
    contractor = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    beneficiary_id = db.Column(db.String(32), db.ForeignKey('beneficiary.beneficiary_id'), nullable=True)
    updates = db.relationship('ConstructionUpdate', backref='project', lazy=True, 
                             foreign_keys='ConstructionUpdate.project_id')
    
    def __repr__(self):
        return f'<Project {self.project_id}>'
        
    def to_dict(self):
        return {
            'id': self.project_id,
            'beneficiaryName': self.beneficiaryName,
            'location': self.location,
            'district': self.district,
            'status': self.status,
            'allocation': self.allocation,
            'completionPercentage': self.completionPercentage,
            'startDate': self.startDate,
            'imageUrl': self.imageUrl,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'description': self.description,
            'end_date': self.end_date,
            'contractor': self.contractor,
            'beneficiary_id': self.beneficiary_id
        }

class ConstructionUpdate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    beneficiaryId = db.Column(db.String(32), nullable=False)
    district = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    constructionStage = db.Column(db.String(100), nullable=False)
    completionPercentage = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(200), nullable=True)
    photos = db.Column(db.String(500), nullable=True)  # Comma-separated URLs
    timestamp = db.Column(db.Integer, nullable=False)
    update_date = db.Column(db.DateTime, default=datetime.utcnow)
    inspector = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=True)

    # Relationships
    project_id = db.Column(db.String(32), db.ForeignKey('project.project_id'), nullable=True)
    user = db.relationship('User', backref=db.backref('construction_updates', lazy=True))
    
    def __repr__(self):
        return f'<ConstructionUpdate {self.id} for {self.beneficiaryId} by {self.username}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    title = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Notification {self.id} for User {self.user_id}>'

class PlotImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(db.String(32), db.ForeignKey('beneficiary.beneficiary_id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    house_designs = db.relationship('HouseDesign', backref='plot_image', lazy=True)
    
    def __repr__(self):
        return f'<PlotImage {self.id} for {self.beneficiary_id}>'

class HouseDesign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(db.String(32), db.ForeignKey('beneficiary.beneficiary_id'), nullable=False)
    plot_image_id = db.Column(db.Integer, db.ForeignKey('plot_image.id'), nullable=False)
    design_type = db.Column(db.String(50), nullable=False)  # Traditional, Modern, Minimalist, etc.
    image_url = db.Column(db.String(255), nullable=False)
    blueprint_url = db.Column(db.String(255), nullable=True)
    interior_url = db.Column(db.String(255), nullable=True)
    exterior_url = db.Column(db.String(255), nullable=True)
    building_cost = db.Column(db.Float, nullable=False)
    labor_cost = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_selected = db.Column(db.Boolean, default=False)
    is_approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<HouseDesign {self.id} for {self.beneficiary_id}>'

class SiteVisit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey('beneficiary.id'), nullable=False)
    nodal_officer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False) # User ID of the Nodal Officer
    
    scheduled_date = db.Column(db.Date, nullable=True)
    schedule_notes = db.Column(db.Text, nullable=True) # Notes by Nodal officer when scheduling
    
    visit_conducted_date = db.Column(db.DateTime, nullable=True)
    construction_stage_observed = db.Column(db.String(100), nullable=True)
    completion_percentage_observed = db.Column(db.Integer, nullable=True)
    visit_remarks = db.Column(db.Text, nullable=True) # Remarks by Nodal officer after visit
    
    # Location captured during visit
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    location_accuracy = db.Column(db.Float, nullable=True) # Accuracy in meters
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    beneficiary = db.relationship('Beneficiary', backref=db.backref('site_visits', lazy='dynamic'))
    nodal_officer = db.relationship('User', backref=db.backref('conducted_site_visits', lazy='dynamic'))

    # Relationship for visit photos
    photos = db.relationship('SiteVisitPhoto', backref='site_visit', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<SiteVisit {self.id} for Beneficiary {self.beneficiary_id} on {self.scheduled_date or self.visit_conducted_date}>'

class SiteVisitPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    site_visit_id = db.Column(db.Integer, db.ForeignKey('site_visit.id'), nullable=False)
    image_filename = db.Column(db.String(255), nullable=False) # Store filename, actual file in UPLOAD_FOLDER/site_visits/
    caption = db.Column(db.String(255), nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SiteVisitPhoto {self.image_filename} for Visit {self.site_visit_id}>'
