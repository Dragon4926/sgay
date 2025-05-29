from flask import Blueprint, current_app, session, jsonify, request
from datetime import datetime, timedelta
from app import db
from models import OTP, Beneficiary, User
import random
import logging

auth_bp = Blueprint('auth', __name__)

logger = logging.getLogger(__name__)

from . import routes
