from flask import Blueprint, render_template, request, send_file
from models import AuditLog
from datetime import datetime, timedelta
from flask_login import login_required
from openpyxl import Workbook
from io import BytesIO
from audit_log import log_user_export

bp = Blueprint('logs', __name__)

@bp.route('/logs')
@login_required
def view_logs():
    page = request.args.get('page', 1, type=int)
    days = request.args.get('days', 7, type=int)
    level = request.args.get('level', 'all')
    action = request.args.get('action', 'all')
    user = request.args.get('user', '')
    
    # Base query
    query = AuditLog.query
    
    # Filter by date
    if days > 0:
        date_limit = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.timestamp >= date_limit)
    
    # Filter by level if specified
    if level != 'all':
        query = query.filter(AuditLog.level == level.upper())
        
    # Filter by action if specified
    if action != 'all':
        query = query.filter(AuditLog.action == action)
        
    # Filter by user if specified
    if user:
        query = query.filter(AuditLog.user.ilike(f'%{user}%'))
    
    # Get distinct actions for filter dropdown
    distinct_actions = AuditLog.query.with_entities(AuditLog.action).distinct().all()
    actions = sorted([action[0] for action in distinct_actions])
    
    # Order by timestamp descending and paginate
    logs = query.order_by(AuditLog.timestamp.desc()).paginate(page=page, per_page=50, error_out=False)
    
    return render_template('logs.html', 
                         logs=logs,
                         current_days=days,
                         current_level=level,
                         current_action=action,
                         current_user=user,
                         available_actions=actions)

@bp.route('/logs/export', methods=['POST'])
@login_required
def export_logs():
    # Récupérer les mêmes filtres que la vue
    days = request.form.get('days', 7, type=int)
    level = request.form.get('level', 'all')
    action = request.form.get('action', 'all')
    user = request.form.get('user', '')
    
    # Base query
    query = AuditLog.query
    
    # Appliquer les mêmes filtres que la vue
    if days > 0:
        date_limit = datetime.utcnow() - timedelta(days=days)
        query = query.filter(AuditLog.timestamp >= date_limit)
    
    if level != 'all':
        query = query.filter(AuditLog.level == level.upper())
        
    if action != 'all':
        query = query.filter(AuditLog.action == action)
        
    if user:
        query = query.filter(AuditLog.user.ilike(f'%{user}%'))
    
    # Récupérer tous les logs filtrés
    logs = query.order_by(AuditLog.timestamp.desc()).all()
    
    # Créer le fichier Excel
    wb = Workbook()
    ws = wb.active
    ws.title = "Audit Logs"
    
    # En-têtes
    headers = ['Date', 'Utilisateur', 'Action', 'Détails', 'Niveau', 'IP']
    ws.append(headers)
    
    # Ajouter les données
    for log in logs:
        ws.append([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.user,
            log.action,
            log.details,
            log.level,
            log.ip_address
        ])
    
    # Créer le fichier en mémoire
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    
    # Logger l'export
    log_user_export(
        action='Export Logs',
        search_term=f'days={days}, level={level}, action={action}, user={user}',
        attributes=headers,
        record_count=len(logs),
        export_format='Excel'
    )
    
    return send_file(
        output,
        as_attachment=True,
        download_name='audit_logs.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
