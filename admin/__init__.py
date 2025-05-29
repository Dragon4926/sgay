from flask import Blueprint

# Create the blueprint first
admin_bp = Blueprint('admin', __name__,
                     template_folder='../templates/admin',
                     url_prefix='/admin',
                     static_folder='../static')

# Import views after blueprint definition to avoid circular imports                     
from . import routes 