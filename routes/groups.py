from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, jsonify
import urllib.parse
from routes.export import check_sensitive_attributes
from ldap_utils import get_ldap_connection, get_all_groups, get_user, search_users
from ldap3 import MODIFY_ADD, MODIFY_DELETE, SUBTREE
from audit_log import log_user_action
from io import BytesIO
import pandas as pd
from datetime import datetime

bp = Blueprint('groups', __name__, url_prefix='/groups')

@bp.route('/')
def list_groups():
    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
        per_page = int(request.args.get('per_page', 30))
        conn = get_ldap_connection()
        search_term = request.args.get('search', '').strip().lower()
        group_type = request.args.get('type')
        if group_type not in ['security', 'distribution']:
            group_type = None
        groups_dict = get_all_groups(conn, group_type)
        
        # Convert dictionary to list of tuples (dn, cn) and filter/sort by CN
        groups_list = sorted(
            [(dn, name) for dn, name in groups_dict.items() 
             if not search_term or search_term in name.lower()],
            key=lambda x: x[1].lower()
        )
        total = len(groups_list)
        
        # Calculate start/end indices with bounds checking
        start = (page - 1) * per_page
        if start >= total:
            # If start is beyond total, adjust page to last valid page
            page = ((total - 1) // per_page) + 1 if total > 0 else 1
            start = (page - 1) * per_page
        
        # Calculate end index with bounds checking
        end = start + per_page
        if end > total:
            end = total
            
        paginated_groups = groups_list[start:end] if total > 0 else []
        
        log_user_action('List Groups', f'User viewed the list of groups. Page {page} with {len(paginated_groups)} groups out of {total}')
        return render_template('group_management.html', groups=paginated_groups, page=page, per_page=per_page, total=total)
    except Exception as e:
        flash(f'Une erreur est survenue lors du chargement des groupes: {str(e)}', 'danger')
        return render_template('group_management.html', groups=[], page=1, per_page=30, total=0)

@bp.route('/<string:group_dn>/members')
def group_members(group_dn):
    conn = get_ldap_connection()
    conn.search(group_dn, '(objectClass=group)', attributes=['member'])
    members = []
    if conn.entries and hasattr(conn.entries[0], 'member'):
        for member_dn in conn.entries[0].member.values:
            conn.search(member_dn, '(objectClass=user)', attributes=['sn', 'givenName', 'sAMAccountName'])
            if conn.entries:
                members.append(conn.entries[0])
    log_user_action('View Group Members', f'User viewed members of group: {group_dn}')
    return render_template('group_members.html', members=members, group_dn=group_dn)

@bp.route('/search_users', methods=['POST'])
def search_users_for_group():
    search_term = request.form.get('search_term', '')
    group_dn = request.form.get('group_dn', '')
    
    print(f"Searching users with term: {search_term}")
    print(f"Group DN: {group_dn}")
    
    if len(search_term) < 3:
        return {'users': []}
        
    conn = get_ldap_connection()
    
    # Get current group members first
    existing_members = set()
    if group_dn:
        print(f"Fetching members for group: {group_dn}")
        conn.search(group_dn, '(objectClass=group)', attributes=['member'])
        if conn.entries and hasattr(conn.entries[0], 'member'):
            # Normalize member DNs
            existing_members = {dn.lower() for dn in conn.entries[0].member.values}
            print(f"Found existing members: {existing_members}")
        else:
            print("No members found in group or no member attribute")
    
    # Get search results
    attributes = ['displayName', 'sAMAccountName', 'mail', 'distinguishedName']
    search_result = search_users(conn, search_term, attributes=attributes)
    
    users = []
    for entry in search_result['users']:
        print(f"Checking user: {entry.entry_dn}")
        if entry.entry_dn.lower() not in existing_members:
            print(f"Adding user {entry.entry_dn} to results (not in group)")
            users.append({
                'displayName': entry.displayName.value if hasattr(entry, 'displayName') else '',
                'sAMAccountName': entry.sAMAccountName.value if hasattr(entry, 'sAMAccountName') else '',
                'mail': entry.mail.value if hasattr(entry, 'mail') else '',
                'dn': entry.entry_dn
            })
        else:
            print(f"Skipping user {entry.entry_dn} (already in group)")
    
    return jsonify({'users': users})

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

@bp.route('/<string:group_dn>/add_member', methods=['POST'])
def add_group_member(group_dn):
    user_dns = [urllib.parse.unquote(dn) for dn in request.form.get('user_dns', '').split('|') if dn]
    print(f"Adding members to group {group_dn}: {user_dns}")
    if not user_dns or not user_dns[0]:
        flash('Aucun utilisateur sélectionné', 'warning')
        return redirect(url_for('groups.group_members', group_dn=group_dn))

    conn = get_ldap_connection()
    success_count = 0
    error_count = 0

    for user_dn in user_dns:
        conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
        print(f"LDAP modify result for {user_dn}: {conn.result}")
        if conn.result['result'] == 0:
            success_count += 1
            log_user_action('Add Group Member', f'Added user {user_dn} to group {group_dn}')
        else:
            error_count += 1
            print(f"Error adding user {user_dn} to group {group_dn}: {conn.result['description']}")
            log_user_action('Add Group Member Error', f'Failed to add user {user_dn} to group {group_dn}. Error: {conn.result["description"]}')

    if success_count > 0:
        flash(f'{success_count} membre(s) ajouté(s) au groupe avec succès', 'success')
    if error_count > 0:
        flash(f'Erreur lors de l\'ajout de {error_count} membre(s)', 'danger')
    
    return redirect(url_for('groups.group_members', group_dn=group_dn))

@bp.route('/<path:group_dn>/export')
def export_group_members(group_dn):
    attributes = request.args.get('attributes', 'sn,givenName,samAccountName').split(',')

    conn = get_ldap_connection()
    # Obtenir les membres du groupe
    conn.search(group_dn, '(objectClass=group)', attributes=['member'])
    
    members_data = []
    if conn.entries and hasattr(conn.entries[0], 'member'):
        for member_dn in conn.entries[0].member.values:
            # Rechercher les attributs spécifiques pour chaque membre
            conn.search(member_dn, '(objectClass=person)', attributes=attributes)
            if conn.entries:
                member = conn.entries[0]
                member_data = {}
                for attr in attributes:
                    # Gérer les attributs qui peuvent ne pas exister
                    if hasattr(member, attr):
                        value = getattr(member, attr).value
                        member_data[attr] = str(value) if value else ''
                    else:
                        member_data[attr] = ''
                members_data.append(member_data)

    if not members_data:
        flash('Aucun membre trouvé dans le groupe', 'warning')
        return redirect(url_for('groups.list_groups'))

    # Créer le DataFrame pandas
    df = pd.DataFrame(members_data)

    # Renommer les colonnes pour l'affichage
    column_names = {
        'sn': 'Nom',
        'givenName': 'Prénom',
        'samAccountName': 'Utilisateur',
        'company': 'Entreprise',
        'department': 'Service',
        'distinguishedName': 'Identifiant Unique AD',
        'employeeID': 'Matricule',
        'ipPhone': 'Téléphone IP',
        'lastLogon': 'Dernière Connexion',
        'manager': 'Responsable',
        'mobile': 'Téléphone Mobile',
        'title': 'Poste',
        'whenCreated': 'Date de Création du Compte'
    }
    df = df.rename(columns=column_names)

    # Convert any timezone-aware columns to naive and format lastLogon
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)
    # Convert any timezone-aware columns to naive and format datetime columns
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.tz_localize(None)
        if col == 'Date de Création du Compte':
            df[col] = pd.to_datetime(df[col], errors='coerce').apply(lambda x: x.strftime('%H:%M %d/%m/%Y') if not pd.isnull(x) else '')
        if col == 'Dernière Connexion':
            df[col] = pd.to_datetime(df[col], errors='coerce').apply(lambda x: x.strftime('%H:%M %d/%m/%Y') if not pd.isnull(x) else '')

    # Créer le fichier Excel en mémoire
    excel_file = BytesIO()
    df.to_excel(excel_file, index=False, engine='openpyxl')
    excel_file.seek(0)

    # Générer le nom du fichier avec la date
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'export_groupe_{timestamp}.xlsx'

    log_user_action('Export Group Members', f'Exported members from group {group_dn} with attributes: {", ".join(attributes)}')

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )

@bp.route('/api/create', methods=['POST'])
def create_group():
    try:
        data = request.get_json()
        name = data.get('name')
        group_type = data.get('type')
        parent_ou = data.get('parent_ou')

        scope = data.get('scope')

        if not all([name, group_type, scope, parent_ou]):
            return jsonify({'error': 'Tous les champs sont requis'}), 400

        if group_type not in ['security', 'distribution']:
            return jsonify({'error': 'Type de groupe invalide'}), 400

        if scope not in ['domainLocal', 'global', 'universal']:
            return jsonify({'error': 'Étendue de groupe invalide'}), 400

        # Map de correspondance entre type/scope et valeur groupType
        group_type_map = {
            ('security', 'domainLocal'): '-2147483644',     # 0x80000004
            ('distribution', 'domainLocal'): '4',           # 0x00000004
            ('security', 'global'): '-2147483646',          # 0x80000002
            ('distribution', 'global'): '2',                # 0x00000002
            ('security', 'universal'): '-2147483640',       # 0x80000008
            ('distribution', 'universal'): '8'              # 0x00000008
        }

        conn = get_ldap_connection()
        
        # Build group DN
        group_dn = f'CN={name},{parent_ou}'
        
        # Set group type
        group_class = ['top', 'group']
        group_attrs = {
            'objectClass': group_class,
            'cn': name,
            'sAMAccountName': name,
            'groupType': group_type_map[(group_type, scope)]
        }

        # Create group
        conn.add(group_dn, attributes=group_attrs)
        
        if conn.result['result'] == 0:
            log_user_action('Create Group', f'Created group {group_dn} of type {group_type}')
            return jsonify({'message': 'Groupe créé avec succès'}), 200
        else:
            error_msg = conn.result.get('description', 'Unknown error')
            log_user_action('Create Group Error', f'Failed to create group {group_dn}. Error: {error_msg}')
            return jsonify({'error': f'Erreur lors de la création du groupe: {error_msg}'}), 500

    except Exception as e:
        log_user_action('Create Group Error', f'Exception while creating group: {str(e)}')
        return jsonify({'error': f'Une erreur est survenue: {str(e)}'}), 500

@bp.route('/api/<path:group_dn>/delete', methods=['DELETE'])
def delete_group(group_dn):
    try:
        conn = get_ldap_connection()
        
        # Check if group exists and get its members
        conn.search(group_dn, '(objectClass=group)', attributes=['member'])
        if not conn.entries:
            return jsonify({'error': 'Groupe non trouvé'}), 404
            
        # Delete group
        conn.delete(group_dn)
        
        if conn.result['result'] == 0:
            log_user_action('Delete Group', f'Deleted group {group_dn}')
            return jsonify({'message': 'Groupe supprimé avec succès'}), 200
        else:
            error_msg = conn.result.get('description', 'Unknown error')
            log_user_action('Delete Group Error', f'Failed to delete group {group_dn}. Error: {error_msg}')
            return jsonify({'error': f'Erreur lors de la suppression du groupe: {error_msg}'}), 500
            
    except Exception as e:
        log_user_action('Delete Group Error', f'Exception while deleting group {group_dn}: {str(e)}')
        return jsonify({'error': f'Une erreur est survenue: {str(e)}'}), 500

@bp.route('/<string:group_dn>/remove_member/<string:user_dn>')
def remove_group_member(group_dn, user_dn):
    conn = get_ldap_connection()
    conn.modify(group_dn, {'member': [(MODIFY_DELETE, [user_dn])]})
    if conn.result['result'] == 0:
        flash('Membre retiré du groupe avec succès', 'success')
        log_user_action('Remove Group Member', f'Removed user {user_dn} from group {group_dn}')
    else:
        flash(f'Erreur lors du retrait du membre: {conn.result["description"]}', 'danger')
        log_user_action('Remove Group Member Error', f'Failed to remove user {user_dn} from group {group_dn}. Error: {conn.result["description"]}')
    return redirect(url_for('groups.group_members', group_dn=group_dn))
