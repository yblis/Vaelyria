from flask import Blueprint, send_file, request, jsonify
from ldap_utils import get_ldap_connection, search_users
from openpyxl import Workbook
from io import BytesIO
from audit_log import log_user_export

bp = Blueprint('export', __name__)

# Liste des attributs exportés
EXPORT_ATTRIBUTES = ['sn', 'givenName', 'sAMAccountName', 'mail', 'company', 'department', 'title']

# Liste des attributs sensibles
SENSITIVE_ATTRIBUTES = ['mobile', 'employeeID', 'telephoneNumber']

def check_sensitive_attributes(selected_attributes):
    """
    Vérifie si des attributs sensibles sont sélectionnés.
    Retourne la liste des attributs sensibles trouvés.
    """
    return [attr for attr in selected_attributes if attr in SENSITIVE_ATTRIBUTES]

@bp.route('/check-sensitive', methods=['POST'])
def check_sensitive():
    """
    Route pour vérifier les attributs sensibles avant l'export.
    """
    selected_attributes = request.json.get('attributes', [])
    sensitive_found = check_sensitive_attributes(selected_attributes)
    
    return jsonify({
        'has_sensitive': bool(sensitive_found),
        'sensitive_attributes': sensitive_found
    })

@bp.route('/export', methods=['POST'])
def export_users():
    search_term = request.form['search_term']
    conn = get_ldap_connection()
    users = search_users(conn, search_term)

    wb = Workbook()
    ws = wb.active
    ws.title = "Utilisateurs AD"

    # Définir les en-têtes
    headers = ['Nom', 'Prénom', 'Nom d\'utilisateur', 'Email', 'Société', 'Département', 'Fonction']
    ws.append(headers)

    # Ajouter les données des utilisateurs
    for user in users:
        ws.append([
            user.sn.value,
            user.givenName.value,
            user.sAMAccountName.value,
            user.mail.value if hasattr(user, 'mail') else '',
            user.company.value if hasattr(user, 'company') else '',
            user.department.value if hasattr(user, 'department') else '',
            user.title.value if hasattr(user, 'title') else ''
        ])

    # Créer un fichier en mémoire
    output = BytesIO()
    wb.save(output)
    output.seek(0)

    # Log l'export avec les détails enrichis
    log_user_export(
        action='Export Users',
        search_term=search_term,
        attributes=EXPORT_ATTRIBUTES,
        record_count=len(users),
        export_format='Excel'
    )

    return send_file(
        output,
        as_attachment=True,
        download_name='utilisateurs_ad.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
