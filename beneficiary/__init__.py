from flask import Blueprint

beneficiary_bp = Blueprint('beneficiary', __name__,
                        template_folder='../templates/beneficiary',
                        url_prefix='/beneficiary',
                        static_folder='../static')

# Import routes after blueprint creation to avoid circular imports
from . import routes 