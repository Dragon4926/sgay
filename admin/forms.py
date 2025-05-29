from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SelectField, TextAreaField, IntegerField
from wtforms import BooleanField, DateField, SubmitField, DecimalField, MultipleFileField
from wtforms.validators import DataRequired, Email, Length, EqualTo, Optional, NumberRange

# User Management Forms
class UserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=4, max=25)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    role = SelectField('Role', choices=[
        ('Admin', 'Admin'),
        ('Nodal Officer', 'Nodal Officer'),
        ('State Authority', 'State Authority'),
        ('Central Authority', 'Central Authority')
    ])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    phone = StringField('Phone', validators=[Length(max=20)])
    password = PasswordField('Password', validators=[
        Optional(),
        Length(min=8, message="Password must be at least 8 characters long")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        EqualTo('password', message='Passwords must match')
    ])
    is_active = BooleanField('Active Account')
    submit = SubmitField('Save User')

# Beneficiary Forms
class BeneficiaryVerificationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    district = SelectField('District', choices=[
        ('East Sikkim', 'East Sikkim'),
        ('West Sikkim', 'West Sikkim'),
        ('North Sikkim', 'North Sikkim'),
        ('South Sikkim', 'South Sikkim'),
        ('Pakyong', 'Pakyong'),
        ('Soreng', 'Soreng')
    ])
    village = StringField('Village/Ward', validators=[DataRequired(), Length(max=100)])
    contact_number = StringField('Contact Number', validators=[Length(max=20)])
    aadhar_number = StringField('Aadhar Number', validators=[Length(max=20)])
    annual_income = IntegerField('Annual Income (₹)', validators=[DataRequired(), NumberRange(min=0)])
    family_members = IntegerField('Number of Family Members', validators=[DataRequired(), NumberRange(min=1)])
    category = SelectField('Category', choices=[
        ('General', 'General'),
        ('SC', 'Scheduled Caste'),
        ('ST', 'Scheduled Tribe'),
        ('OBC', 'Other Backward Class'),
        ('Minority', 'Minority')
    ])
    land_ownership = SelectField('Land Ownership Status', choices=[
        ('Own', 'Own Land'),
        ('Family', 'Family Land'),
        ('Leased', 'Leased Land'),
        ('None', 'No Land')
    ])
    property_area = IntegerField('Property Area (sq. ft.)', validators=[Optional()])
    verification_notes = TextAreaField('Verification Notes', validators=[Length(max=500)])
    verification_status = SelectField('Verification Status', choices=[
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('need_info', 'Need Additional Information')
    ])
    documents_verified = BooleanField('All Documents Verified')
    physical_verification = BooleanField('Physical Verification Completed')
    verification_photos = MultipleFileField('Verification Photos', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    submit = SubmitField('Submit Verification')

# Project Forms
class ProjectInspectionForm(FlaskForm):
    project_id = StringField('Project ID', validators=[DataRequired()])
    beneficiary_id = StringField('Beneficiary ID', validators=[DataRequired()])
    construction_stage = SelectField('Construction Stage', choices=[
        ('foundation', 'Foundation'),
        ('plinth', 'Plinth Level'),
        ('walls', 'Wall Construction'),
        ('roof', 'Roof Level'),
        ('finishing', 'Finishing Work'),
        ('completed', 'Completed')
    ])
    completion_percentage = IntegerField('Completion Percentage', validators=[
        DataRequired(),
        NumberRange(min=0, max=100, message='Percentage must be between 0 and 100')
    ])
    quality_rating = SelectField('Quality Rating', choices=[
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('below_average', 'Below Average'),
        ('poor', 'Poor')
    ])
    inspection_notes = TextAreaField('Inspection Notes', validators=[Length(max=500)])
    next_disbursement_recommended = BooleanField('Recommend Next Disbursement')
    inspection_photos = MultipleFileField('Inspection Photos', validators=[
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    submit = SubmitField('Submit Inspection Report')

# Financial Forms
class FundSanctionForm(FlaskForm):
    batch_id = StringField('Batch ID', validators=[DataRequired()])
    district = SelectField('District', choices=[
        ('East Sikkim', 'East Sikkim'),
        ('West Sikkim', 'West Sikkim'),
        ('North Sikkim', 'North Sikkim'),
        ('South Sikkim', 'South Sikkim'),
        ('Pakyong', 'Pakyong'),
        ('Soreng', 'Soreng')
    ])
    beneficiary_count = IntegerField('Number of Beneficiaries', validators=[DataRequired(), NumberRange(min=1)])
    total_amount = DecimalField('Total Amount (₹)', validators=[DataRequired(), NumberRange(min=0)])
    installment_type = SelectField('Installment Type', choices=[
        ('first', 'First Installment'),
        ('second', 'Second Installment'),
        ('third', 'Third Installment'),
        ('special', 'Special Case')
    ])
    sanction_notes = TextAreaField('Sanction Notes', validators=[Length(max=500)])
    sanction_status = SelectField('Sanction Status', choices=[
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('need_info', 'Need Additional Information'),
        ('partial_approve', 'Partially Approved')
    ])
    submit = SubmitField('Process Sanction')

# Budget Allocation Form
class BudgetAllocationForm(FlaskForm):
    fiscal_year = StringField('Fiscal Year', validators=[DataRequired()])
    total_allocation = DecimalField('Total Allocation (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    
    # District-wise allocation fields
    east_sikkim = DecimalField('East Sikkim (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    west_sikkim = DecimalField('West Sikkim (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    north_sikkim = DecimalField('North Sikkim (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    south_sikkim = DecimalField('South Sikkim (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    pakyong = DecimalField('Pakyong (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    soreng = DecimalField('Soreng (₹ Cr)', validators=[DataRequired(), NumberRange(min=0)])
    
    allocation_notes = TextAreaField('Allocation Notes', validators=[Length(max=500)])
    submit = SubmitField('Save Allocation') 

# Construction Image Upload Form
class ConstructionImageUploadForm(FlaskForm):
    project_id = StringField('Project ID', validators=[DataRequired(), Length(max=32)])
    image = FileField('Construction Image', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    construction_stage = SelectField('Construction Stage', choices=[
        ('Site Preparation', 'Site Preparation'),
        ('Foundation', 'Foundation'),
        ('Plinth', 'Plinth Level'),
        ('Walls', 'Wall Construction'),
        ('Roofing', 'Roofing'),
        ('Finishing', 'Finishing Work'),
        ('Completed', 'Completed')
    ], validators=[DataRequired()])
    completion_percentage = IntegerField('Completion Percentage', validators=[
        DataRequired(),
        NumberRange(min=0, max=100, message='Percentage must be between 0 and 100')
    ])
    description = TextAreaField('Description/Notes', validators=[Optional(), Length(max=500)])
    location = StringField('Location', validators=[Optional(), Length(max=200)])
    latitude = DecimalField('Latitude', validators=[Optional()], places=6)
    longitude = DecimalField('Longitude', validators=[Optional()], places=6)
    submit = SubmitField('Upload Image') 