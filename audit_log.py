from werkzeug.exceptions import HTTPException
from flask import jsonify, request, session
from flask_login import current_user
import re
from models import db, AuditLog

def log_user_export(action, search_term, attributes, record_count, export_format, level='INFO'):
    """
    Log details of a user export action with full context.
    """
    user = current_user.username if hasattr(current_user, 'username') else 'Anonymous'
    ip_address = request.remote_addr
    session_id = session.get('id', 'No session')
    cleaned_attributes = clean_sensitive_data(str(attributes))

    # Créer le message de log
    details = (
        f"Export réalisé. "
        f"Terme de recherche: '{search_term}', "
        f"Attributs: {cleaned_attributes}, "
        f"Nombre d'enregistrements: {record_count}, "
        f"Format: {export_format}"
    )
    
    log_entry = AuditLog(
        user=user,
        action=action,
        details=details,
        ip_address=ip_address,
        session_id=session_id,
        level=level.upper()
    )
    
    db.session.add(log_entry)
    db.session.commit()

def clean_sensitive_data(data):
    """
    Clean sensitive data from logs.
    """
    patterns = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),
        (r'\b(?:\+\d{1,3}[-\s]?)?\d{9,15}\b', '[PHONE]'),
        (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP]')
    ]
    for pattern, replacement in patterns:
        data = re.sub(pattern, replacement, str(data))
    return data

def log_user_action(action, details, level='INFO'):
    """
    Log user actions with details in database.
    """
    user = current_user.username if hasattr(current_user, 'username') else 'Anonymous'
    ip_address = request.remote_addr
    session_id = session.get('id', 'No session')
    cleaned_details = clean_sensitive_data(details)
    
    log_entry = AuditLog(
        user=user,
        action=action,
        details=cleaned_details,
        ip_address=ip_address,
        session_id=session_id,
        level=level.upper()
    )
    
    db.session.add(log_entry)
    db.session.commit()

def setup_audit_logging(app):
    """
    Set up audit logging for the Flask application.
    """
    @app.errorhandler(Exception)
    def log_exception(error):
        log_user_action('Exception', str(error), level='ERROR')
        response = jsonify(message=str(error))
        response.status_code = (error.code if isinstance(error, HTTPException) else 500)
        return response
