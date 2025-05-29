from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField, RadioField
from wtforms.validators import DataRequired, Email, Length, Optional

# Profile form for beneficiaries
class BeneficiaryProfileForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(max=20)])
    address = StringField('Address', validators=[DataRequired(), Length(max=200)])
    village = StringField('Village', validators=[DataRequired(), Length(max=100)])
    bank_name = StringField('Bank Name', validators=[Optional(), Length(max=100)])
    account_number = StringField('Account Number', validators=[Optional(), Length(max=50)])
    ifsc_code = StringField('IFSC Code', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Update Profile')

# Document upload form
class DocumentUploadForm(FlaskForm):
    document_type = SelectField('Document Type', choices=[
        ('aadhar', 'Aadhar Card'),
        ('income', 'Income Certificate'),
        ('land', 'Land Ownership Documents'),
        ('family', 'Family Certificate'),
        ('bank', 'Bank Account Details'),
        ('other', 'Other Documents')
    ])
    document_file = FileField('Document File', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'png', 'pdf'], 'Images and PDFs only!')
    ])
    description = StringField('Description', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Upload Document')

# Update request form
class UpdateRequestForm(FlaskForm):
    request_type = SelectField('Request Type', choices=[
        ('construction', 'Construction Update'),
        ('payment', 'Payment Inquiry'),
        ('technical', 'Technical Issue'),
        ('documentation', 'Documentation Issue'),
        ('other', 'Other')
    ])
    subject = StringField('Subject', validators=[DataRequired(), Length(max=100)])
    message = TextAreaField('Message', validators=[DataRequired(), Length(max=500)])
    priority = SelectField('Priority', choices=[
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High')
    ])
    submit = SubmitField('Submit Request')

# Plot Image Upload Form for AI Architect
class PlotImageUploadForm(FlaskForm):
    plot_image = FileField('Upload Plot Image', validators=[
        DataRequired(),
        FileAllowed(['jpg', 'jpeg', 'png'], 'Images only!')
    ])
    notes = TextAreaField('Additional Notes', validators=[Optional(), Length(max=500)], 
                         description="Describe any specific requirements or preferences for your house design.")
    submit = SubmitField('Generate House Designs')

# House Design Selection Form
class HouseDesignSelectionForm(FlaskForm):
    design_id = RadioField('Select Design', validators=[DataRequired()], coerce=int)
    comments = TextAreaField('Comments or Requests for Modifications', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Select This Design')

# House Design Finalization Form
class HouseDesignFinalizationForm(FlaskForm):
    confirm = RadioField('Confirm Design Submission', validators=[DataRequired()], 
                        choices=[('yes', 'Yes, submit this design'), ('no', 'No, I need more changes')],
                        default='no')
    final_comments = TextAreaField('Final Comments', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Submit for Approval') 