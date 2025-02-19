from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify, send_file, g
from datetime import datetime, timezone
from ldap_utils import (get_ldap_connection, search_users, get_user, modify_user, create_user, 
                       move_to_trash, lock_unlock_user, get_all_groups, generate_unique_phone_number, 
                       trigger_ad_azure_sync, get_service_profiles, get_service_profile,
                       get_user_statistics, get_group_statistics, get_security_statistics, 
                       get_activity_statistics, restore_user)
from ldap3 import MODIFY_REPLACE
from models import LDAPConfig, db
from ldap3 import MODIFY_REPLACE, MODIFY_ADD, SUBTREE, LEVEL, BASE
from audit_log import log_user_action
from flask import jsonify
import json
from io import BytesIO
import pandas as pd
from datetime import datetime

bp = Blueprint('users', __name__)

@bp.route('/get_username_config')
def get_username_config():
    """Get the LDAP username pattern configuration"""
    config = LDAPConfig.get_config()
    if config:
        return jsonify({
            'config': {
                'username_pattern_order': config.username_pattern_order or 'NOM_PRENOM',
                'username_first_part_chars': config.username_first_part_chars or '3',
                'username_second_part_chars': config.username_second_part_chars or '3',
                'username_separator': config.username_separator or ''
            }
        })
    return jsonify({
        'config': {
            'username_pattern_order': 'NOM_PRENOM',
            'username_first_part_chars': '3',
            'username_second_part_chars': '3',
            'username_separator': ''
        }
    })

@bp.route('/get_email_config')
def get_email_config():
    """Get the LDAP email pattern configuration"""
    config = LDAPConfig.get_config()
    if config:
        return jsonify({
            'config': {
                'email_pattern_order': config.email_pattern_order or 'NOM_PRENOM',
                'email_first_part_chars': config.email_first_part_chars or '3',
                'email_second_part_chars': config.email_second_part_chars or '3',
                'email_separator': config.email_separator or '.'
            }
        })
    return jsonify({
        'config': {
            'email_pattern_order': 'NOM_PRENOM',
            'email_first_part_chars': '*',
            'email_second_part_chars': '*',
            'email_separator': '.'
        }
    })

@bp.route('/')
def dashboard():
    log_user_action('View Dashboard', 'User accessed the dashboard')
    return render_template('dashboard.html')

@bp.route('/search', methods=['GET', 'POST'])
def search():
    search_term = request.form.get('search_term') or request.args.get('search_term', '')
    page = request.args.get('page', 1, type=int)
    account_filters = [f for f in request.args.getlist('account_filters[]') if f]

    # Retrieve the selected OU (full DN) from the GET parameter
    selected_ou = request.args.get('selected_ou', '').strip()

    # Build the base LDAP filter
    filters = []
    if search_term:
        filters.append(f'(|(cn=*{search_term}*)(sAMAccountName=*{search_term}*)(mail=*{search_term}*))')

    uac_filters = []
    for uac in account_filters:
        uac_filters.append(f'(userAccountControl={uac})')
    if len(uac_filters) > 1:
        filters.append(f'(|{"".join(uac_filters)})')
    elif len(uac_filters) == 1:
        filters.append(uac_filters[0])

    # Filtrer par email
    if request.args.get('has_email'):
        filters.append('(mail=*)')

    # Filtrer par domaine
    domain_filter = request.args.get('domain_filter')
    if domain_filter:
        filters.append(f'(mail=*@{domain_filter})')

    base_filter = '(&(objectClass=user)(objectCategory=person)'
    if filters:
        base_filter += ''.join(filters)
    base_filter += ')'

    # Utiliser le selected_ou comme base de recherche ou la base par défaut
    if selected_ou:
        # S'assurer que le selected_ou est correctement formaté
        ou_parts = [part for part in selected_ou.split(',') if part.startswith('OU=')]
        if ou_parts:
            search_base = ','.join(ou_parts) + ',' + current_app.config['BASE_DN']
            print(f"[Debug] Using OU as search base: {search_base}")
        else:
            search_base = current_app.config['BASE_DN']
            print(f"[Debug] No valid OU parts found, using default base: {search_base}")
    else:
        search_base = current_app.config['BASE_DN']
        print(f"[Debug] No OU selected, using default base: {search_base}")

    conn = get_ldap_connection()
    print("[Debug] Début de la route /get_unique_ous")
    conn.search(
        search_base,
        base_filter,
        attributes=['sn', 'givenName', 'sAMAccountName', 'mail', 'userAccountControl'],
        search_scope=SUBTREE
    )
    entries = conn.entries
    total = len(entries)

    per_page = 50
    offset = (page - 1) * per_page
    # Récupération des paramètres de tri
    sort_column = request.args.get('sort_column')
    sort_direction = request.args.get('sort_direction', 'asc')

    # Application du tri si demandé
    if sort_column:
        column_mapping = {
            'nom': 'sn',
            'prenom': 'givenName',
            'username': 'sAMAccountName',
            'email': 'mail',
            'ou': 'entry_dn'
        }
        ldap_attr = column_mapping.get(sort_column)
        if ldap_attr:
            if sort_column == 'ou':
                entries.sort(
                    key=lambda x: '/'.join([part.split('=')[1] for part in x.entry_dn.split(',') if part.startswith('OU=')][::-1]),
                    reverse=sort_direction == 'desc'
                )
            else:
                entries.sort(
                    key=lambda x: (getattr(x, ldap_attr).value if hasattr(x, ldap_attr) and getattr(x, ldap_attr).value is not None else '').lower(),
                    reverse=sort_direction == 'desc'
                )

    paginated_entries = entries[offset : offset + per_page]

    results = {
        'users': paginated_entries,
        'total': total,
        'page': page,
        'total_pages': (total + per_page - 1) // per_page,
        'sort_column': sort_column,
        'sort_direction': sort_direction
    }

    log_user_action('User Search', f'Search term: {search_term}, Filters: {account_filters}, Selected OU: {selected_ou}, Sort: {sort_column} {sort_direction}')
    log_user_action('User Search Results', f'Found {results["total"]} users')

    # Récupérer les domaines depuis la configuration
    config = LDAPConfig.get_config()
    domains = config.domains.split('\n') if config and config.domains else []
    domains = [d.strip() for d in domains if d.strip()]

    return render_template(
        'user_search.html',
        users=results['users'],
        search_term=search_term,
        current_page=results['page'],
        total_pages=results['total_pages'],
        total_users=results['total'],
        domains=domains
    )


@bp.route('/search/export')
def export_search_results():
    search_term = request.args.get('search_term', '')
    attributes_str = request.args.get('attributes', 'sn,givenName,samAccountName')
    attributes = attributes_str.split(',')
    account_filters = [f for f in request.args.getlist('account_filters[]') if f]

    conn = get_ldap_connection()

    filters = []
    if search_term:
        filters.append(f'(|(cn=*{search_term}*)(sAMAccountName=*{search_term}*)(mail=*{search_term}*))')
    uac_filters = []
    if account_filters:
        for uac in account_filters:
            uac_filters.append(f'(userAccountControl={uac})')
        if len(uac_filters) > 1:
            filters.append(f'(|{"".join(uac_filters)})')
        else:
            filters.append(uac_filters[0])

    # Filtrer par email
    if request.args.get('has_email'):
        filters.append('(mail=*)')

    # Filtrer par domaine 
    domain_filter = request.args.get('domain_filter')
    if domain_filter:
        filters.append(f'(mail=*@{domain_filter})')

    base_filter = '(&(objectClass=user)(objectCategory=person)'
    if filters:
        base_filter += ''.join(filters)
    base_filter += ')'

    selected_ou = request.args.get('selected_ou', '').strip()
    
    # Utiliser le selected_ou comme base de recherche ou la base par défaut
    if selected_ou:
        # S'assurer que le selected_ou est correctement formaté
        ou_parts = [part for part in selected_ou.split(',') if part.startswith('OU=')]
        if ou_parts:
            search_base = ','.join(ou_parts) + ',' + current_app.config['BASE_DN']
            print(f"[Export Debug] Using OU as search base: {search_base}")
        else:
            search_base = current_app.config['BASE_DN']
            print(f"[Export Debug] No valid OU parts found, using default base: {search_base}")
    else:
        search_base = current_app.config['BASE_DN']
        print(f"[Export Debug] No OU selected, using default base: {search_base}")
    conn.search(search_base, base_filter, attributes=['*'], search_scope=SUBTREE)
    results = {'users': conn.entries, 'total': len(conn.entries)}
    print(f"[Export Debug] Found {len(results['users'])} users to export")

    users_data = []
    for user in results['users']:
        user_data = {}
        for attr in attributes:
            if hasattr(user, attr):
                value = getattr(user, attr).value
                user_data[attr] = ', '.join(str(v) for v in value) if isinstance(value, list) else (str(value) if value else '')
            else:
                user_data[attr] = ''
        users_data.append(user_data)

    if not users_data:
        flash('Aucun utilisateur trouvé', 'warning')
        return redirect(url_for('users.search', search_term=search_term))

    df = pd.DataFrame(users_data)
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
    df = df.rename(columns={col: column_names.get(col, col) for col in df.columns})

    if 'lastLogon' in attributes:
        df['Dernière Connexion'] = pd.to_datetime(df['Dernière Connexion'], errors='coerce').apply(lambda x: x.strftime('%H:%M %d/%m/%Y') if pd.notnull(x) else '')
    if 'whenCreated' in attributes:
        df['Date de Création du Compte'] = pd.to_datetime(df['Date de Création du Compte'], errors='coerce').apply(lambda x: x.strftime('%H:%M %d/%m/%Y') if pd.notnull(x) else '')

    excel_file = BytesIO()
    df.to_excel(excel_file, index=False, engine='openpyxl')
    excel_file.seek(0)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'export_utilisateurs_{timestamp}.xlsx'

    log_user_action('Export Users', f'Exported users search results for term: {search_term}')

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/statistics/export/<string:report_type>')
def export_statistics(report_type):
    """Export statistics data to Excel"""
    conn = get_ldap_connection()
    stats = get_activity_statistics(conn)
    
    users_data = []
    filename = ""
    headers = []

    if report_type == "recent_creations":
        filename = "utilisateurs_crees_30j.xlsx"
        headers = ['Nom Prénom', 'Date de création']
        for name, date in stats['recent_creations']:
            users_data.append({
                'Nom Prénom': name,
                'Date de création': date.strftime('%d/%m/%Y')
            })
    
    elif report_type == "disabled_users":
        filename = "utilisateurs_desactives.xlsx"
        headers = ['Utilisateur', 'Dernière connexion']
        for name, date in stats['disabled_users']:
            users_data.append({
                'Utilisateur': name,
                'Dernière connexion': date.strftime('%d/%m/%Y %H:%M') if date and date.year > 1601 else 'Jamais'
            })
    
    elif report_type == "inactive_users":
        filename = "utilisateurs_inactifs_3mois.xlsx"
        headers = ['Utilisateur', 'Dernière connexion']
        for name, date in stats['inactive_users_3months']:
            users_data.append({
                'Utilisateur': name,
                'Dernière connexion': date.strftime('%d/%m/%Y %H:%M')
            })

    elif report_type == "locked_users":
        filename = "utilisateurs_verrouilles_30j.xlsx"
        headers = ['Nom Prénom', 'Date de verrouillage']
        for name, date in stats['locked_users']:
            users_data.append({
                'Nom Prénom': name,
                'Date de verrouillage': date.strftime('%d/%m/%Y %H:%M')
            })

    elif report_type == "empty_groups":
        filename = "groupes_vides.xlsx"
        headers = ['Nom du groupe']
        for group_name in stats['empty_groups']:
            users_data.append({
                'Nom du groupe': group_name
            })
    else:
        flash('Type de rapport invalide', 'danger')
        return redirect(url_for('users.statistics'))

    if not users_data:
        flash('Aucune donnée à exporter', 'warning')
        return redirect(url_for('users.statistics'))

    # Créer le DataFrame pandas
    df = pd.DataFrame(users_data)

    # Créer le fichier Excel en mémoire
    excel_file = BytesIO()
    df.to_excel(excel_file, index=False, engine='openpyxl')
    excel_file.seek(0)

    # Générer le nom du fichier avec la date
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{filename.split(".")[0]}_{timestamp}.xlsx'

    return send_file(
        excel_file,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=filename
    )


@bp.route('/edit/<string:dn>', methods=['GET', 'POST'])
def edit_user(dn):
    conn = get_ldap_connection()
    user = get_user(conn, dn)

    # Récupérer les groupes de l'utilisateur
    user_groups = []
    if hasattr(user, 'memberOf'):
        for group_dn in user.memberOf.values:
            conn.search(group_dn, '(objectClass=*)', attributes=['cn'])
            if conn.entries:
                user_groups.append({
                    'dn': group_dn,
                    'name': conn.entries[0].cn.value
                })

    # Récupérer tous les groupes disponibles
    all_groups = get_all_groups(conn)
    # Exclure les groupes dont l'utilisateur est déjà membre
    available_groups = {dn: name for dn, name in all_groups.items() 
                      if dn not in [g['dn'] for g in user_groups]}
    if request.method == 'GET':
        log_user_action('Access Edit User Page', f'Accessed edit page for user: {dn}')
        
        # Créer un dictionnaire avec les attributs de l'utilisateur
        user_attrs = {}
        for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon', 'accountExpires']:
            if hasattr(user, attr):
                try:
                    user_attrs[attr] = getattr(user, attr).value
                except:
                    user_attrs[attr] = ''
            else:
                user_attrs[attr] = ''
        
        # Si displayName n'existe pas, le créer à partir de givenName et sn
        if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
            user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
        
        # Créer un objet qui combine les attributs LDAP standard et nos attributs personnalisés
        user_data = {
            'entry_dn': user.entry_dn,
            'attrs': user_attrs
        }
        
        return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)
    if request.method == 'POST':
        # Only include attributes that have non-empty values
        changes = {}
        # Créer le displayName à partir de sn et givenName si non fourni
        display_name = request.form.get('displayName')
        if not display_name:
            sn = request.form.get('sn', '')
            given_name = request.form.get('givenName', '')
            display_name = f"{given_name} {sn}".strip()
            
        attributes = {
            'displayName': display_name,
            'mail': request.form.get('mail', ''),
            'company': request.form.get('company', ''),
            'department': request.form.get('department', ''),
            'title': request.form.get('title', ''),
            'sn': request.form.get('sn', ''),
            'givenName': request.form.get('givenName', ''),
            'sAMAccountName': request.form.get('samAccountName', ''),
            'mobile': request.form.get('mobile', ''),
            'ipPhone': request.form.get('ipPhone', '')
        }
        
        for attr, value in attributes.items():
            if value.strip():  # Only include non-empty values
                changes[attr] = [(MODIFY_REPLACE, [value.strip()])]

        # Handle expiration date
        expiration_date = request.form.get('expiration_date')
        if expiration_date:
            try:
                expiration_date = datetime.strptime(expiration_date, '%d-%m-%Y').replace(tzinfo=timezone.utc)
                epoch_start = datetime(1601, 1, 1, tzinfo=timezone.utc)
                account_expires = int((expiration_date - epoch_start).total_seconds() * 10**7)
                changes['accountExpires'] = [(MODIFY_REPLACE, [str(account_expires)])]
            except ValueError as e:
                flash('Format de date invalide. Utilisez DD-MM-YYYY', 'warning')
                return redirect(url_for('users.edit_user', dn=dn))
        elif 'disable_expiration' in request.form:
            changes['accountExpires'] = [(MODIFY_REPLACE, ['9223372036854775807'])]  # Never expires

        # Ajouter le manager s'il est fourni
        manager = request.form.get('manager', '').strip()
        if manager:
            changes['manager'] = [(MODIFY_REPLACE, [manager])]

        # Vérifier si l'emplacement a changé
        new_ou = request.form.get('selectedOU')
        if new_ou and new_ou != ','.join(dn.split(',')[1:]):
            # Construire le nouveau DN
            cn = dn.split(',')[0]
            new_dn = f"{cn},{new_ou}"
            
            # Déplacer l'utilisateur
            try:
                result = conn.modify_dn(dn, cn, new_superior=new_ou)
                if not result:
                    flash(f'Erreur lors du déplacement: {conn.result["description"]}', 'danger')
                    log_user_action('Move User Error', f'Failed to move user from {dn} to {new_dn}')
                    user = get_user(conn, dn)
                    # Format user data
                    user_attrs = {}
                    for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
                        if hasattr(user, attr):
                            try:
                                user_attrs[attr] = getattr(user, attr).value
                            except:
                                user_attrs[attr] = ''
                        else:
                            user_attrs[attr] = ''
                    if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
                        user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
                    user_data = {
                        'entry_dn': user.entry_dn,
                        'attrs': user_attrs
                    }
                    return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)
                dn = new_dn
            except Exception as e:
                flash(f'Erreur lors du déplacement: {str(e)}', 'danger')
                log_user_action('Move User Error', f'Failed to move user from {dn} to {new_dn}. Error: {str(e)}')
                user = get_user(conn, dn)
                # Format user data
                user_attrs = {}
                for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
                    if hasattr(user, attr):
                        try:
                            user_attrs[attr] = getattr(user, attr).value
                        except:
                            user_attrs[attr] = ''
                    else:
                        user_attrs[attr] = ''
                if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
                    user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
                user_data = {
                    'entry_dn': user.entry_dn,
                    'attrs': user_attrs
                }
                return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)

        # Appliquer les modifications d'attributs
        changes_without_uac = {k: v for k, v in changes.items() if k != 'userAccountControl'}
        if changes_without_uac:
            result = modify_user(conn, dn, changes_without_uac)
            if result['result'] != 0:
                flash(f'Erreur lors de la modification: {result["description"]}', 'danger')
                log_user_action('Edit User Error', f'Failed to modify user: {dn}. Error: {result["description"]}')
                user = get_user(conn, dn)
                # Format user data
                user_attrs = {}
                for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
                    if hasattr(user, attr):
                        try:
                            user_attrs[attr] = getattr(user, attr).value
                        except:
                            user_attrs[attr] = ''
                    else:
                        user_attrs[attr] = ''
                if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
                    user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
                user_data = {
                    'entry_dn': user.entry_dn,
                    'attrs': user_attrs
                }
                return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)

        # Gestion des états du compte
        try:
            print("[User Edit Debug] Starting account state modifications")
            
            print("[User Edit Debug] Starting account modifications")
            user = get_user(conn, dn)
            if not user:
                flash('Utilisateur introuvable', 'warning')
                user = get_user(conn, dn)
                # Format user data
                user_attrs = {}
                for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
                    if hasattr(user, attr):
                        try:
                            user_attrs[attr] = getattr(user, attr).value
                        except:
                            user_attrs[attr] = ''
                    else:
                        user_attrs[attr] = ''
                if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
                    user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
                user_data = {
                    'entry_dn': user.entry_dn,
                    'attrs': user_attrs
                }
                return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)

            print("[User Edit Debug] Current user state:")
            print(f"- DN: {dn}")
            print(f"- Lockout Time: {user.lockoutTime.value if hasattr(user, 'lockoutTime') else 'Not set'}")
            print(f"- UAC: {user.userAccountControl.value if hasattr(user, 'userAccountControl') else 'Not set'}")

            # Gérer d'abord l'état du compte (actif/inactif)
            is_active = 'accountActive' in request.form
            uac_value = 512 if is_active else 514
            print(f"[User Edit Debug] Setting account state - Active: {is_active}, UAC Value: {uac_value}")
            
            uac_result = modify_user(conn, dn, {
                'userAccountControl': [(MODIFY_REPLACE, [uac_value])]
            })
            print(f"[User Edit Debug] UAC modification result: {uac_result}")

            # Gérer ensuite le verrouillage
            should_unlock = 'accountLocked' in request.form
            print(f"[User Edit Debug] Should unlock account: {should_unlock}")
            
            lock_result = lock_unlock_user(conn, dn, lock=not should_unlock)
            print(f"[User Edit Debug] Lock/unlock result: {lock_result}")
            print(f"[User Edit Debug] UAC modification result: {uac_result}")

            if uac_result['result'] != 0:
                flash(f'Erreur lors de la modification de l\'état du compte: {uac_result["description"]}', 'danger')
                log_user_action('Edit User Error', f'Failed to modify account state: {dn}')
                user = get_user(conn, dn)
                return render_template('user_edit.html', user=user, groups=available_groups, user_groups=user_groups)

            flash('Utilisateur modifié avec succès', 'success')
            log_user_action('Edit User', f'Successfully modified user: {dn}')
            
            # Récupérer l'utilisateur mis à jour pour afficher les dernières modifications
            user = get_user(conn, dn)
            # Créer un dictionnaire avec les attributs de l'utilisateur
            user_attrs = {}
            for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
                if hasattr(user, attr):
                    try:
                        user_attrs[attr] = getattr(user, attr).value
                    except:
                        user_attrs[attr] = ''
                else:
                    user_attrs[attr] = ''
            
            # Si displayName n'existe pas, le créer à partir de givenName et sn
            if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
                user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()

            # Handle expiration date
            if 'accountExpires' in user_attrs:
                no_expiry_values = ['9223372036854775807', '9999-12-31 23:59:59.999999+00:00']
                if user_attrs['accountExpires'] in no_expiry_values or str(user_attrs['accountExpires']) in no_expiry_values:
                    user_attrs['accountExpires'] = ''
                elif user_attrs['accountExpires']:
                    try:
                        # Try parsing as date first
                        if isinstance(user_attrs['accountExpires'], str) and 'UTC' in user_attrs['accountExpires']:
                            expiration_date = datetime.fromisoformat(user_attrs['accountExpires'].replace('UTC', '+00:00'))
                            user_attrs['accountExpires'] = expiration_date.strftime('%d-%m-%Y')
                        else:
                            # Try parsing as Windows timestamp
                            account_expires_int = int(user_attrs['accountExpires'])
                            if account_expires_int > 0:
                                epoch_start = datetime(1601, 1, 1, tzinfo=timezone.utc)
                                expiration_date = epoch_start + timedelta(seconds=account_expires_int/10**7)
                                user_attrs['accountExpires'] = expiration_date.strftime('%d-%m-%Y')
                            else:
                                user_attrs['accountExpires'] = ''
                    except (ValueError, TypeError):
                        user_attrs['accountExpires'] = ''
                else:
                    user_attrs['accountExpires'] = ''
            
            # Créer un objet qui combine les attributs LDAP standard et nos attributs personnalisés
            user_data = {
                'entry_dn': user.entry_dn,
                'attrs': user_attrs
            }
            return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)

        except Exception as e:
            flash(f'Erreur lors de la modification des états: {str(e)}', 'danger')
            log_user_action('Edit User Error', f'Failed to modify user states: {dn}. Error: {str(e)}')
            # En cas d'erreur, rester sur la page avec l'utilisateur actuel
            user = get_user(conn, dn)
            # Format user data
            user_attrs = {}
            for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
                if hasattr(user, attr):
                    try:
                        user_attrs[attr] = getattr(user, attr).value
                    except:
                        user_attrs[attr] = ''
                else:
                    user_attrs[attr] = ''
            if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
                user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
            user_data = {
                'entry_dn': user.entry_dn,
                'attrs': user_attrs
            }
            return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)
    # Format user data
    user_attrs = {}
    for attr in ['displayName', 'mail', 'company', 'department', 'title', 'sn', 'givenName', 'sAMAccountName', 'mobile', 'ipPhone', 'userAccountControl', 'manager', 'whenCreated', 'lastLogon']:
        if hasattr(user, attr):
            try:
                user_attrs[attr] = getattr(user, attr).value
            except:
                user_attrs[attr] = ''
        else:
            user_attrs[attr] = ''
    if not user_attrs['displayName'] and user_attrs['givenName'] and user_attrs['sn']:
        user_attrs['displayName'] = f"{user_attrs['givenName']} {user_attrs['sn']}".strip()
    user_data = {
        'entry_dn': user.entry_dn,
        'attrs': user_attrs
    }
    return render_template('user_edit.html', user=user_data, groups=available_groups, user_groups=user_groups)


@bp.route('/add_to_group/<string:dn>', methods=['POST'])
def add_to_group(dn):
    try:
        conn = get_ldap_connection()
        group_dn = request.form.get('group_dn')
        
        if not group_dn:
            return jsonify({'success': False, 'error': 'DN du groupe manquant'}), 400

        # Ajouter l'utilisateur au groupe
        result = conn.modify(group_dn, {'member': [(MODIFY_ADD, [dn])]})
        
        if result:
            log_user_action('Add to Group', f'Added user {dn} to group {group_dn}')
            return jsonify({'success': True})
        else:
            log_user_action('Add to Group Error', f'Failed to add user {dn} to group {group_dn}')
            return jsonify({'success': False, 'error': conn.result['description']}), 400

    except Exception as e:
        log_user_action('Add to Group Error', f'Error adding user {dn} to group: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/remove_from_group/<string:dn>', methods=['POST'])
def remove_from_group(dn):
    try:
        conn = get_ldap_connection()
        group_dn = request.form.get('group_dn')
        
        if not group_dn:
            return jsonify({'success': False, 'error': 'DN du groupe manquant'}), 400

        # Rechercher le groupe pour obtenir la liste des membres
        conn.search(group_dn, '(objectClass=*)', attributes=['member'])
        if not conn.entries:
            return jsonify({'success': False, 'error': 'Groupe non trouvé'}), 404
            
        # Retirer l'utilisateur du groupe
        current_members = conn.entries[0].member.values if hasattr(conn.entries[0], 'member') else []
        new_members = [m for m in current_members if m != dn]
        
        result = conn.modify(group_dn, {'member': [(MODIFY_REPLACE, new_members)]})
        
        if result:
            log_user_action('Remove from Group', f'Removed user {dn} from group {group_dn}')
            return jsonify({'success': True})
        else:
            log_user_action('Remove from Group Error', f'Failed to remove user {dn} from group {group_dn}')
            return jsonify({'success': False, 'error': conn.result['description']}), 400

    except Exception as e:
        log_user_action('Remove from Group Error', f'Error removing user {dn} from group: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'GET':
        log_user_action('Access Create User Page', 'Accessed create user page', level='INFO')
        service_profiles = get_service_profiles()
        config = LDAPConfig.get_config()
        return render_template('user_create.html', 
                             service_profiles=service_profiles,
                             tenant=config.tenant if config else '')

    if request.method == 'POST':
        log_user_action('Create User Started', 'Received user creation form submission', level='INFO')
        
        # Récupération et validation des données du formulaire
        nom = request.form['nom'].upper()
        prenom = request.form['prenom']
        sync_ad_azure = 'sync_ad_azure' in request.form
        
        # Vérification de l'existence de l'email
        service_profile_id = request.form.get('service_profile')
        profile = get_service_profile(int(service_profile_id)) if service_profile_id else None
        if not profile or not profile.domains:
            flash('Un profil de service avec un domaine est requis', 'warning')
            return redirect(url_for('users.create'))
        
        domaine = profile.domains[0]
        base_mail = f"{prenom}.{nom}"
        if profile.mail_suffix:
            base_mail += profile.mail_suffix
        email = f"{base_mail}@{domaine}".lower()
        
        # Vérifié si l'email existe déjà dans l'AD
        conn = get_ldap_connection()
        search_filter = f'(&(objectClass=user)(mail={email}))'
        conn.search(current_app.config['BASE_DN'], search_filter, attributes=['mail'])
        if len(conn.entries) > 0:
            flash(f'Un utilisateur avec l\'adresse e-mail {email} existe déjà', 'warning')
            return redirect(url_for('users.create'))
        
        # Récupération du profil de service
        service_profile_id = request.form.get('service_profile')
        profile = None
        if service_profile_id and service_profile_id.strip():
            try:
                profile = get_service_profile(int(service_profile_id))
            except ValueError:
                log_user_action('Create User Error', 'Invalid service profile ID', level='ERROR')
                flash('Profil de service invalide', 'warning')
                return redirect(url_for('users.create'))
        
        if not profile:
            flash('Un profil de service est requis', 'warning')
            return redirect(url_for('users.create'))
        
        # Get the domain from the service profile
        if not profile.domains or not profile.domains[0]:
            flash('Le profil de service doit avoir un domaine configuré', 'warning')
            return redirect(url_for('users.create'))
        
        domaine = profile.domains[0]  # Use the first domain from the profile

        # Get email pattern configuration
        config = LDAPConfig.get_config()
        if config:
            email_order = config.email_pattern_order or 'NOM_PRENOM'
            first_chars = config.email_first_part_chars or '*'  # Changed default to '*' for full name
            second_chars = config.email_second_part_chars or '*'  # Changed default to '*' for full name
            separator = config.email_separator or '.'
            
            # Apply email pattern configuration
            first = prenom if email_order == 'NOM_PRENOM' else nom
            second = nom if email_order == 'NOM_PRENOM' else prenom
            
            # Apply length rules
            if first_chars != '*':
                first = first[:int(first_chars)]
            if second_chars != '*':
                second = second[:int(second_chars)]
            
            base_mail = (first + separator + second).lower()
        else:
            # Default pattern if no config 
            base_mail = f"{prenom}.{nom}".lower()  # Keep dot as default separator
        
        log_user_action('Create User Input', 
                       f'Initial form data: Nom={nom}, Prenom={prenom}, ' +
                       f'Profile={profile.name} (domaine={domaine}), ' +
                       f'Email={base_mail}@{domaine}, ' +
                       f'Sync AD/Azure={sync_ad_azure}', 
                       level='DEBUG')
        # Récupération du mot de passe par défaut depuis la configuration
        print("[Password Debug] Récupération de la configuration LDAP")
        config = LDAPConfig.get_config()
        if config:
            print("[Password Debug] Configuration LDAP trouvée, récupération du mot de passe")
            mot_de_passe = config.get_decrypted_password()
        else:
            print("[Password Debug] Pas de configuration LDAP, utilisation du mot de passe par défaut")
            mot_de_passe = 'Secret20@estunmotdepasse!'
        print(f"[Password Debug] Mot de passe défini: {'***' if mot_de_passe else 'Non défini'}")

        # Générer les attributs utilisateur avec les suffixes du profil
        samaccountname = request.form.get('username')
        if not samaccountname:
            samaccountname = f"{prenom[0]}{nom}".lower()
        
        if profile.samaccountname_suffix:
            samaccountname += profile.samaccountname_suffix
        
        # Construction du CN avec le suffixe si défini
        cn = f"{nom} {prenom}"
        if profile.commonname_suffix:
            cn += profile.commonname_suffix

        # Détermination de l'OU
        ou_path = profile.ou
        log_user_action('OU Selection', f'Using OU from service profile: {ou_path}', level='DEBUG')

        # Configuration email et proxy addresses
        config = LDAPConfig.get_config()
        tenant = config.tenant if config else ''
        log_user_action('Email Config', f'Using tenant: {tenant}', level='DEBUG')

        # Construire l'email selon le pattern configuré
        email_order = config.email_pattern_order if config else 'NOM_PRENOM'
        first_chars = config.email_first_part_chars if config else '*'
        second_chars = config.email_second_part_chars if config else '*'
        separator = config.email_separator if config else '.'

        # Construire les parties selon le pattern
        first = ''
        second = ''
        if email_order == 'PRENOM':
            first = prenom
            if first_chars != '*':
                first = first[:int(first_chars)]
            base_mail = first
        elif email_order == 'NOM':
            first = nom
            if first_chars != '*':
                first = first[:int(first_chars)]
            base_mail = first
        elif email_order == 'PRENOM_NOM':
            first = prenom
            second = nom
            if first_chars != '*':
                first = first[:int(first_chars)]
            if second_chars != '*':
                second = second[:int(second_chars)]
            base_mail = first + (separator if separator else '') + second
        else:  # NOM_PRENOM
            first = nom
            second = prenom
            if first_chars != '*':
                first = first[:int(first_chars)]
            if second_chars != '*':
                second = second[:int(second_chars)]
            base_mail = first + (separator if separator else '') + second


        # Add profile mail suffix if defined
        if profile.mail_suffix:
            base_mail += profile.mail_suffix

        mail = f"{base_mail}@{domaine}"
        
        # Construction du mailNickname avec le suffixe si défini (optionnel)
        mail_nickname = base_mail.lower()
        if profile.mailnickname_suffix and profile.mailnickname_suffix != profile.mail_suffix:
            mail_nickname += profile.mailnickname_suffix
        # Ne pas inclure mail_nickname dans le log s'il n'est pas défini
        log_msg = f'Generated email: {mail}'
        if mail_nickname:
            log_msg += f', Nickname: {mail_nickname}'
        log_user_action('Email Generation', log_msg, level='DEBUG')

        # Configuration des proxy addresses
        proxy_addresses = []
        if tenant:
            tenant_address = f"smtp:{prenom}.{nom}@{tenant}.onmicrosoft.com".lower()
            proxy_addresses.append(tenant_address)
            log_user_action('Proxy Addresses', f'Added tenant address: {tenant_address}', level='DEBUG')
        
        primary_smtp = f"SMTP:{mail}"
        proxy_addresses.append(primary_smtp)
        log_user_action('Proxy Addresses', 
                       f'Final proxy addresses: {proxy_addresses}', 
                       level='DEBUG')

        # Construction du prénom avec le suffixe si défini
        givenname = prenom
        if profile.givenname_suffix:
            givenname += profile.givenname_suffix

        # Configuration complète de l'utilisateur
        log_user_action('User Configuration', 'Building complete user configuration', level='INFO')
        user_info = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'cn': cn,
            'sn': nom,
            'givenName': givenname,
            'displayName': cn,
            'name': cn,
            'sAMAccountName': samaccountname,
            'mail': mail,
            'userPrincipalName': mail,
            'distinguishedName': f"CN={cn},{ou_path}",
            'userAccountControl': '514'  # Désactivé par défaut avant l'activation
        }

        # Handle expiration date
        expiration_date = request.form.get('expiration_date')
        if expiration_date:
            try:
                expiration_date = datetime.strptime(expiration_date, '%d-%m-%Y').replace(tzinfo=timezone.utc)
                epoch_start = datetime(1601, 1, 1, tzinfo=timezone.utc)
                account_expires = int((expiration_date - epoch_start).total_seconds() * 10**7)
                user_info['accountExpires'] = str(account_expires)
            except ValueError as e:
                flash('Format de date invalide. Utilisez DD-MM-YYYY', 'warning')
                return redirect(url_for('users.create'))

        # Ajouter mailNickname uniquement s'il est défini
        if mail_nickname:
            user_info['mailNickName'] = mail_nickname

        # Configuration des adresses proxy avec le suffixe si défini
        proxy_addresses = []
        if tenant:
            tenant_address = f"smtp:{mail_nickname}@{tenant}.onmicrosoft.com".lower()
            proxy_addresses.append(tenant_address)

        smtp_address = mail
        if profile.proxyaddresses_suffix and profile.proxyaddresses_suffix != profile.mail_suffix:
            smtp_base = f"{prenom}.{nom}{profile.proxyaddresses_suffix}"
            smtp_address = f"{smtp_base}@{domaine}".lower()

        proxy_addresses.append(f"SMTP:{smtp_address}")
        user_info['proxyAddresses'] = proxy_addresses

        # Configuration de l'adresse cible avec le suffixe si défini
        # Ajouter targetAddress uniquement s'il y a un suffixe spécifique
        if profile.targetaddress_suffix and profile.targetaddress_suffix != profile.proxyaddresses_suffix:
            target_base = f"{prenom}.{nom}{profile.targetaddress_suffix}"
            target_address = f"{target_base}@{domaine}".lower()
            user_info['targetAddress'] = f"SMTP:{target_address}"

        # Récupération des valeurs du profil de service
        service_profile_id = request.form.get('service_profile')
        profile = None
        if service_profile_id and service_profile_id.strip():
            try:
                profile = get_service_profile(int(service_profile_id))
            except ValueError:
                pass

        # Ajout des attributs du profil
        if profile:
            if hasattr(profile, 'function') and profile.function:
                user_info['title'] = profile.function
            if hasattr(profile, 'service') and profile.service:
                user_info['department'] = profile.service
            if hasattr(profile, 'society') and profile.society:
                user_info['company'] = profile.society
        # Les attributs company, department et function sont gérés uniquement via le profil de service

        # Gestion de la téléphonie IP et connexion LDAP
        conn = get_ldap_connection()
        log_user_action('LDAP Connection', 'LDAP connection established for user creation', level='DEBUG')

        # Gestion de la téléphonie IP basée sur le profil de service
        if profile and hasattr(profile, 'ip_telephony') and profile.ip_telephony:
            try:
                # Rechercher tous les numéros de téléphone existants dans l'AD
                search_filter = '(ipPhone=tel:+33*)'
                conn.search(current_app.config['BASE_DN'], search_filter, attributes=['ipPhone'])
                
                existing_numbers = []
                for entry in conn.entries:
                    if hasattr(entry, 'ipPhone'):
                        num = entry.ipPhone.value
                        if num and len(num) == 11:  # Vérifie que le numéro a 11 caractères
                            try:
                                existing_numbers.append(int(num[7:]))  # Extraire le numéro après "tel:+33"
                            except ValueError:
                                continue

                if existing_numbers:
                    # Trouver le premier trou dans la séquence
                    existing_numbers.sort()
                    next_number = None
                    for i in range(len(existing_numbers) - 1):
                        if existing_numbers[i + 1] - existing_numbers[i] > 1:
                            next_number = existing_numbers[i] + 1
                            break
                    
                    # Si pas de trou, prendre le numéro suivant
                    if next_number is None:
                        next_number = existing_numbers[-1] + 1
                else:
                    next_number = 1000  # Commencer à 1000 si aucun numéro n'existe

                # S'assurer que le numéro a 4 chiffres
                next_number_str = str(next_number).zfill(4)
                user_info['ipPhone'] = f"tel:+33{next_number_str}"

            except Exception as e:
                log_user_action('IP Phone Error', 
                              f'Error assigning IP phone number: {str(e)}', 
                              level='ERROR')
                flash('Erreur lors de l\'attribution du numéro de téléphone', 'danger')
                user_info['ipPhone'] = None  # Don't set ipPhone if there's an error

        log_user_action('Create User Request', f'Starting user creation with info: {user_info}', level='INFO')
        
        result = create_user(conn, user_info)
        
        if result['result'] == 0:
            log_user_action('Create User Progress', 'User created successfully in LDAP, proceeding with password setup', level='INFO')
            if profile:
                if hasattr(profile, 'manager') and profile.manager:
                    conn.modify(user_info['distinguishedName'], {'manager': [(MODIFY_REPLACE, [profile.manager])]})
                    log_user_action('Create User - Manager', f'Set manager from service profile: {profile.manager}', level='INFO')
                if hasattr(profile, 'groups') and profile.groups:
                    for group_dn in profile.groups:
                        conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_info['distinguishedName']])]})
                        log_user_action('Create User - Groups', f'Added user to group from service profile: {group_dn}', level='INFO')
            if mot_de_passe:
                log_user_action('Password Setup', 'Attempting to set user password', level='INFO')
                try:
                    result = conn.extend.microsoft.modify_password(user_info['distinguishedName'], mot_de_passe)
                    if result:
                        log_user_action('Password Setup', 'Password successfully set for user', level='INFO')
                    else:
                        error_msg = f"Failed to set password: {conn.result}"
                        log_user_action('Password Setup Error', error_msg, level='ERROR')
                        print(f"[Password Error] {error_msg}")
                except Exception as e:
                    error_msg = f"Exception during password setup: {str(e)}"
                    log_user_action('Password Setup Error', error_msg, level='ERROR')
                    print(f"[Password Error] {error_msg}")

            log_user_action('Account Activation', 'Attempting to activate user account', level='INFO')
            try:
                activation_result = conn.modify(user_info['distinguishedName'], 
                                             {'userAccountControl': [(MODIFY_REPLACE, [512])]})
                if activation_result:
                    log_user_action('Account Activation', 'User account successfully activated', level='INFO')
                else:
                    log_user_action('Account Activation Error', 
                                  f'Failed to activate account: {conn.result}', 
                                  level='ERROR')
            except Exception as e:
                log_user_action('Account Activation Error', 
                              f'Exception during account activation: {str(e)}', 
                              level='ERROR')

            success_message = 'Utilisateur créé avec succès'
            flash(success_message, 'success')
            log_user_action('Create User Success', 
                          f'User creation completed successfully. DN: {user_info["distinguishedName"]}, ' + 
                          f'Username: {user_info["sAMAccountName"]}, ' +
                          f'Email: {user_info["mail"]}',
                          level='INFO')

            if sync_ad_azure:
                log_user_action('AD Azure Sync', 'Initiating AD/Azure synchronization', level='INFO')
                sync_result = trigger_ad_azure_sync()
                if sync_result:
                    log_user_action('AD Azure Sync', 'AD/Azure synchronization triggered successfully', level='INFO')
                    flash('Synchronisation AD/Azure lancée', 'info')
                else:
                    log_user_action('AD Azure Sync Error', 'Failed to trigger AD/Azure synchronization', level='ERROR')
                    flash('Erreur lors de la synchronisation AD/Azure', 'danger')
            
            # Redirect to edit page after successful creation
            user_cn = f"CN={cn},{ou_path}"  # Construct the DN for redirection
            return redirect(url_for('users.edit_user', dn=user_cn))
        else:
            error_msg = f'Erreur lors de la création: {result["description"]}'
            flash(error_msg, 'danger')
            log_user_action('Create User Error', 
                          f'Failed to create user in LDAP. DN: {user_info["distinguishedName"]}, ' +
                          f'Username: {user_info["sAMAccountName"]}, ' +
                          f'Error: {result["description"]}, ' +
                          f'LDAP Result: {conn.result}', 
                          level='ERROR')
            return redirect(url_for('users.search'))


@bp.route('/trash/<string:dn>', methods=['GET', 'POST'])
def trash_user(dn):
    from models import LDAPConfig
    
    # Get TRASH_OU from database
    config = LDAPConfig.get_config()
    if not config or not config.trash_ou:
        if request.method == 'POST':
            return jsonify({'success': False, 'error': 'Configuration de la corbeille manquante. Veuillez configurer l\'OU Corbeille dans les paramètres LDAP.'}), 500
        flash('Configuration de la corbeille manquante. Veuillez configurer l\'OU Corbeille dans les paramètres LDAP.', 'danger')
        return redirect(url_for('users.search'))
    
    if request.method == 'GET':
        # Handle legacy GET requests for backwards compatibility
        search_term = request.args.get('search_term', '')
        conn = get_ldap_connection()
        user = get_user(conn, dn)
        if not user:
            flash('Utilisateur non trouvé', 'danger')
            return redirect(url_for('users.search', search_term=search_term))
            
        username = user.sAMAccountName.value if hasattr(user, 'sAMAccountName') else 'Unknown'
        
        # First disable the user account
        disable_result = modify_user(conn, dn, {
            'userAccountControl': [(MODIFY_REPLACE, [514])]  # 514 = Disabled account
        })
        
        if disable_result['result'] != 0:
            flash(f'Erreur lors de la désactivation: {disable_result["description"]}', 'danger')
            log_user_action('Trash User Error', f'Failed to disable user: {username} ({dn}). Error: {disable_result["description"]}')
            return redirect(url_for('users.search', search_term=search_term))
        
        # Then move the user to trash
        result = move_to_trash(conn, dn)
        if result['result'] == 0:
            flash('Utilisateur déplacé vers la corbeille et désactivé', 'success')
            log_user_action('Trash User', f'Moved user to trash and disabled: {username} ({dn})')
        else:
            flash(f'Erreur lors du déplacement: {result["description"]}', 'danger')
            log_user_action('Trash User Error', f'Failed to move user to trash: {username} ({dn}). Error: {result["description"]}')
        return redirect(url_for('users.search', search_term=search_term))
    
    # Handle AJAX POST requests
    conn = get_ldap_connection()
    user = get_user(conn, dn)
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404
        
    username = user.sAMAccountName.value if hasattr(user, 'sAMAccountName') else 'Unknown'
    
    # First disable the user account
    disable_result = modify_user(conn, dn, {
        'userAccountControl': [(MODIFY_REPLACE, [514])]  # 514 = Disabled account
    })
    
    if disable_result['result'] != 0:
        log_user_action('Trash User Error', f'Failed to disable user: {username} ({dn}). Error: {disable_result["description"]}')
        return jsonify({
            'success': False,
            'error': f'Erreur lors de la désactivation: {disable_result["description"]}'
        }), 400
    
    # Then move the user to trash
    result = move_to_trash(conn, dn)
    if result['result'] == 0:
        log_user_action('Trash User', f'Moved user to trash and disabled: {username} ({dn})')
        return jsonify({'success': True})
    else:
        log_user_action('Trash User Error', f'Failed to move user to trash: {username} ({dn}). Error: {result["description"]}')
        return jsonify({
            'success': False,
            'error': f'Erreur lors du déplacement: {result["description"]}'
        }), 400

@bp.route('/lock/<string:dn>', methods=['GET', 'POST'])
def lock_user(dn):
    conn = get_ldap_connection()
    user = get_user(conn, dn)
    if not user:
        if request.method == 'POST':
            return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404
        flash('Utilisateur non trouvé', 'danger')
        return redirect(url_for('users.search'))
        
    username = user.sAMAccountName.value if hasattr(user, 'sAMAccountName') else 'Unknown'
    result = lock_unlock_user(conn, dn, lock=True)
    
    if request.method == 'POST':
        if result['result'] == 0:
            log_user_action('Lock User', f'Locked user account: {username} ({dn})')
            return jsonify({'success': True})
        else:
            message = "Droits insuffisants pour verrouiller le compte" if result["description"] == "insufficientAccessRights" else f"Erreur lors du verrouillage: {result['description']}"
            log_user_action('Lock User Error', f'Failed to lock user account: {username} ({dn}). Error: {result["description"]}')
            return jsonify({'success': False, 'error': message}), 400
    else:
        # Handle legacy GET requests
        search_term = request.args.get('search_term', '')
        if result['result'] == 0:
            flash('Compte utilisateur verrouillé', 'success')
            log_user_action('Lock User', f'Locked user account: {username} ({dn})')
        else:
            message = "Droits insuffisants pour verrouiller le compte" if result["description"] == "insufficientAccessRights" else f"Erreur lors du verrouillage: {result['description']}"
            flash(message, 'warning')
            log_user_action('Lock User Error', f'Failed to lock user account: {username} ({dn}). Error: {result["description"]}')
        return redirect(url_for('users.search', search_term=search_term))

@bp.route('/unlock/<string:dn>', methods=['GET', 'POST'])
def unlock_user(dn):
    conn = get_ldap_connection()
    user = get_user(conn, dn)
    if not user:
        if request.method == 'POST':
            return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404
        flash('Utilisateur non trouvé', 'danger')
        return redirect(url_for('users.search'))
        
    username = user.sAMAccountName.value if hasattr(user, 'sAMAccountName') else 'Unknown'
    result = lock_unlock_user(conn, dn, lock=False)
    
    if request.method == 'POST':
        if result['result'] == 0:
            log_user_action('Unlock User', f'Unlocked user account: {username} ({dn})')
            return jsonify({'success': True})
        else:
            log_user_action('Unlock User Error', f'Failed to unlock user account: {username} ({dn}). Error: {result["description"]}')
            return jsonify({'success': False, 'error': f'Erreur lors du déverrouillage: {result["description"]}'}), 400
    else:
        # Handle legacy GET requests
        search_term = request.args.get('search_term', '')
        if result['result'] == 0:
            flash('Compte utilisateur déverrouillé', 'success')
            log_user_action('Unlock User', f'Unlocked user account: {username} ({dn})')
        else:
            flash(f'Erreur lors du déverrouillage: {result["description"]}', 'warning')
            log_user_action('Unlock User Error', f'Failed to unlock user account: {username} ({dn}). Error: {result["description"]}')
        return redirect(url_for('users.search', search_term=search_term))

@bp.route('/search_reference_user', methods=['GET'])
def search_reference_user():
    search_term = request.args.get('term', '')
    if not search_term:
        return jsonify([])
    
    conn = get_ldap_connection()
    search_filter = f'(&(objectClass=user)(|(cn=*{search_term}*)(sAMAccountName=*{search_term}*)))'
    conn.search(current_app.config['BASE_DN'], search_filter, attributes=['cn', 'distinguishedName', 'department', 'company', 'manager'])
    
    results = []
    for entry in conn.entries:
        results.append({
            'value': entry.entry_dn,
            'label': entry.cn.value,
            'department': entry.department.value if hasattr(entry, 'department') else '',
            'company': entry.company.value if hasattr(entry, 'company') else ''
        })
    return jsonify(results)

@bp.route('/get_reference_user', methods=['GET'])
def get_reference_user():
    dn = request.args.get('dn')
    if not dn:
        return jsonify({'error': 'DN non fourni'}), 400
        
    conn = get_ldap_connection()
    user = get_user(conn, dn)
    if not user:
        return jsonify({'error': 'Utilisateur non trouvé'}), 404
        
    user_data = {
        'department': user.department.value if hasattr(user, 'department') else '',
        'company': user.company.value if hasattr(user, 'company') else '',
        'manager': user.manager.value if hasattr(user, 'manager') else '',
        'groups': []
    }
    
    # Récupérer les groupes de l'utilisateur
    conn.search(current_app.config['BASE_DN'],
               f'(&(objectClass=group)(member={dn}))',
               attributes=['cn'])
    user_data['groups'] = [entry.cn.value for entry in conn.entries]
    
    return jsonify(user_data)

@bp.route('/check_username', methods=['GET'])
def check_username():
    username = request.args.get('username')
    profile_id = request.args.get('profile_id')
    conn = get_ldap_connection()
    
    # Si un profil est sélectionné, récupérer son suffixe
    suffix = ""
    if profile_id:
        profile = get_service_profile(int(profile_id))
        if profile and profile.samaccountname_suffix:
            suffix = profile.samaccountname_suffix

    # Vérifier avec le suffixe
    search_filter = f'(&(objectClass=user)(sAMAccountName={username}{suffix}))'
    conn.search(current_app.config['BASE_DN'], search_filter, attributes=['sAMAccountName'])
    exists = len(conn.entries) > 0
    return jsonify({'exists': exists})

@bp.route('/check_samaccountname', methods=['GET'])
def check_samaccountname():
    samaccountname = request.args.get('samaccountname')
    profile_id = request.args.get('profile_id')
    conn = get_ldap_connection()
    
    # Si un profil est sélectionné, récupérer son suffixe
    suffix = ""
    if profile_id:
        profile = get_service_profile(int(profile_id))
        if profile and profile.samaccountname_suffix:
            suffix = profile.samaccountname_suffix

    # Vérifier avec le suffixe
    search_filter = f'(&(objectClass=user)(sAMAccountName={samaccountname}{suffix}))'
    conn.search(current_app.config['BASE_DN'], search_filter, attributes=['sAMAccountName'])
    exists = len(conn.entries) > 0
    return jsonify({'exists': exists})

@bp.route('/get_ldap_tree')
def get_ldap_tree():
    conn = get_ldap_connection()
    base_dn = current_app.config['BASE_DN']
    user_dn = request.args.get('user_dn')
    if not user_dn:
        print("[LDAP Debug] DN non fourni")
        return jsonify({'error': 'DN non fourni'}), 400
    print(f"[LDAP Debug] DN utilisateur: {user_dn}")
    
    def get_children(dn):
        search_filter = '(objectClass=organizationalUnit)'
        print(f"[LDAP Debug] Recherche des OUs dans: {dn}")
        conn.search(dn, search_filter, attributes=['ou'])
        children = []
        for entry in conn.entries:
            print(f"[LDAP Debug] OU trouvée: {entry.entry_dn}")
            children.append({
                'text': entry.ou.value,
                'id': entry.entry_dn,
                'type': 'ou',
                'children': get_children(entry.entry_dn)
            })
        return children

    # Construction de l'arbre
    tree = []
    
    # Racine de l'arbre (domaine)
    domain_parts = base_dn.split(',')
    domain_text = '.'.join(part.split('=')[1] for part in domain_parts if part.startswith('DC='))
    
    # Construire l'arborescence à partir de l'emplacement de l'utilisateur
    def build_tree_from_dn(dn):
        parts = dn.split(',')
        tree = []
        current_level = tree
        for part in reversed(parts):
            if part.startswith('DC='):
                current_level.append({
                    'text': part.split('=')[1],
                    'id': ','.join(parts),
                    'state': {'opened': True},
                    'type': 'root',
                    'children': []
                })
                current_level = current_level[0]['children']
            elif part.startswith('OU='):
                current_level.append({
                    'text': part.split('=')[1],
                    'id': ','.join(parts),
                    'type': 'ou',
                    'children': []
                })
                current_level = current_level[-1]['children']
            if part.startswith('CN='):
                continue
            parts.pop()
        return tree

    try:
        # Extraire les parties du DN
        parts = user_dn.split(',')
        
        # Filtrer les parties pour ne garder que les OU et DC
        filtered_parts = [part for part in parts if part.startswith('OU=') or part.startswith('DC=')]
        
        # Construire l'arbre
        tree = []
        current_path = []
        
        # Commencer par les DC pour construire la racine
        dc_parts = [part for part in filtered_parts if part.startswith('DC=')]
        if dc_parts:
            root_id = ','.join(dc_parts)
            root_text = '.'.join(part.split('=')[1] for part in dc_parts)
            tree = [{
                'text': root_text,
                'id': root_id,
                'state': {'opened': True},
                'type': 'root',
                'children': []
            }]
            current_level = tree[0]['children']
            current_path = dc_parts
            
            # Ajouter les OUs dans l'ordre inverse
            ou_parts = [part for part in filtered_parts if part.startswith('OU=')]
            ou_parts.reverse()
            
            for ou in ou_parts:
                current_path.insert(0, ou)
                current_level.append({
                    'text': ou.split('=')[1],
                    'id': ','.join(current_path),
                    'state': {'opened': True},
                    'type': 'ou',
                    'children': []
                })
                current_level = current_level[-1]['children']
        
        print(f"[LDAP Debug] Arbre LDAP construit: {tree}")
        return jsonify(tree)
    except Exception as e:
        print(f"[LDAP Debug] Erreur lors de la construction de l'arbre LDAP: {str(e)}")
        return jsonify({'error': str(e)}), 500

@bp.route('/reset_password/<string:dn>', methods=['POST'])
def reset_password(dn):
    """
    Reset a user's password and modify account settings
    """
    try:
        conn = get_ldap_connection()
        data = request.get_json()
        
        # Get current user account control value
        user = get_user(conn, dn)
        if not user:
            log_user_action('Reset Password Error', f'User not found: {dn}')
            return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404
        
        current_uac = user.userAccountControl.value
        new_uac = current_uac
        
        # Handle account activation if requested
        if data.get('enable_account') and (current_uac & 0x0002):  # ACCOUNTDISABLE bit is set
            new_uac = current_uac & ~0x0002  # Remove ACCOUNTDISABLE bit
        
        # Handle password never expires flag
        if data.get('never_expire'):
            new_uac = new_uac | 0x10000  # Add DONT_EXPIRE_PASSWORD bit

        # Handle prevent password changes flag
        if data.get('prevent_changes'):
            new_uac = new_uac | 0x0040  # Add PASSWD_CANT_CHANGE bit
        
        # Update userAccountControl if changed
        if new_uac != current_uac:
            result = modify_user(conn, dn, {
                'userAccountControl': [(MODIFY_REPLACE, [new_uac])]
            })
            if not result['result'] == 0:
                log_user_action('Reset Password Error', f'Failed to update userAccountControl for {dn}')
                return jsonify({'success': False, 'error': 'Erreur lors de la modification des paramètres du compte'}), 400
        
        # Reset password using Microsoft AD modify_password method
        try:
            conn.extend.microsoft.modify_password(dn, data['password'])
        except Exception as e:
            log_user_action('Reset Password Error', f'Failed to reset password for {dn}: {str(e)}')
            return jsonify({'success': False, 'error': 'Erreur lors de la réinitialisation du mot de passe'}), 400
        
        # Force password reset at next login if requested
        if data.get('force_reset'):
            result = modify_user(conn, dn, {
                'pwdLastSet': [(MODIFY_REPLACE, ['0'])]
            })
            if not result['result'] == 0:
                log_user_action('Reset Password Warning', f'Failed to set pwdLastSet for {dn}')
                # Continue anyway as the password was successfully reset
        
        log_user_action('Reset Password', f'Successfully reset password for user: {dn}')
        return jsonify({'success': True})
        
    except Exception as e:
        log_user_action('Reset Password Error', f'Exception while resetting password for {dn}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/move/<string:dn>', methods=['POST'])
def move_user(dn):
    """Déplace un utilisateur sans le réactiver"""
    target_ou = request.json.get('target_ou')
    if not target_ou:
        return jsonify({'success': False, 'error': 'OU de destination manquant'}), 400

    conn = get_ldap_connection()
    # Construire le nouveau DN en gardant le CN original
    old_cn = dn.split(',')[0]
    new_dn = f"{old_cn},{target_ou}"
    
    try:
        # Déplacer l'utilisateur vers la nouvelle OU
        result = conn.modify_dn(dn, old_cn, new_superior=target_ou)
        
        if result:
            log_user_action('Move User', f'Successfully moved user from {dn} to {new_dn}')
            return jsonify({'success': True})
        else:
            log_user_action('Move User Error', f'Failed to move user: {dn}. Error: {conn.result["description"]}')
            return jsonify({'success': False, 'error': conn.result['description']}), 400
    except Exception as e:
        log_user_action('Move User Error', f'Exception moving user {dn}: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/restore/<string:dn>', methods=['POST'])
def restore_user_route(dn):
    """Restaure un utilisateur depuis la corbeille"""
    target_ou = request.json.get('target_ou')
    if not target_ou:
        return jsonify({'success': False, 'error': 'OU de destination manquant'}), 400

    conn = get_ldap_connection()
    result = restore_user(conn, dn, target_ou)

    if result['result'] == 0:
        log_user_action('Restore User', f'Successfully restored user from trash: {dn}')
        return jsonify({'success': True})
    else:
        log_user_action('Restore User Error', f'Failed to restore user: {dn}. Error: {result["description"]}')
        return jsonify({'success': False, 'error': result['description']}), 400

@bp.route('/get_unique_ous')
def get_unique_ous():
    conn = get_ldap_connection()
    # Rechercher toutes les OUs directement
    search_filter = '(objectClass=organizationalUnit)'
    try:
        conn.search(
            current_app.config['BASE_DN'],
            search_filter,
            attributes=['distinguishedName'],
            search_scope=SUBTREE
        )
        
        # Extraire et formater les OUs uniques
        unique_ous = set()
        for entry in conn.entries:
            parts = entry.entry_dn.split(',')
            ou_path = []
            for part in parts:
                if part.startswith('OU='):
                    ou_path.append(part[3:])
            if ou_path:  # Seulement si on a des OUs
                ou_path.reverse()  # Inverser l'ordre pour avoir le chemin de gauche à droite
                unique_ous.add('/' + '/'.join(ou_path) + '/')
        
        print(f"[Debug] Found OUs: {sorted(list(unique_ous))}")
        return jsonify(sorted(list(unique_ous)))
    except Exception as e:
        print(f"[Error] Failed to get OUs: {str(e)}")
        return jsonify([]), 500

@bp.route('/delete_user/<string:dn>', methods=['POST'])
def delete_user(dn):
    """Delete a user permanently from AD"""
    conn = get_ldap_connection()
    user = get_user(conn, dn)
    
    if not user:
        return jsonify({'success': False, 'error': 'Utilisateur non trouvé'}), 404
    
    username = user.sAMAccountName.value if hasattr(user, 'sAMAccountName') else 'Unknown'
    
    try:
        result = conn.delete(dn)
        if result:
            log_user_action('Delete User', f'Deleted user from AD: {username} ({dn})')
            return jsonify({'success': True})
        else:
            error_msg = conn.result.get('description', 'Unknown error')
            log_user_action('Delete User Error', f'Failed to delete user: {username} ({dn}). Error: {error_msg}')
            return jsonify({'success': False, 'error': error_msg}), 400
    except Exception as e:
        log_user_action('Delete User Error', f'Exception deleting user: {username} ({dn}). Error: {str(e)}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/statistics')
def statistics():
    """Page des statistiques de l'AD"""
    try:
        conn = get_ldap_connection()
        log_user_action('View Statistics', 'User accessed AD statistics')
        
        try:
            users_stats = get_user_statistics(conn)
        except Exception as e:
            print(f"Error getting user stats: {e}")
            users_stats = {}
            
        try:
            groups_stats = get_group_statistics(conn)
        except Exception as e:
            print(f"Error getting group stats: {e}")
            groups_stats = {}
            
        try:
            security_stats = get_security_statistics(conn)
        except Exception as e:
            print(f"Error getting security stats: {e}")
            security_stats = {}
            
        try:
            activity_stats = get_activity_statistics(conn)
        except Exception as e:
            print(f"Error getting activity stats: {e}")
            activity_stats = {}
        
        stats = {
            'users': users_stats,
            'groups': groups_stats,
            'security': security_stats,
            'activity': activity_stats
        }
        
        return render_template('statistics.html', stats=stats)

    except Exception as e:
        print(f"Erreur lors de la génération des statistiques: {str(e)}")
        flash("Erreur lors de la récupération des statistiques", "danger")
        log_user_action('Statistics Error', f'Failed to generate statistics: {str(e)}')
        return render_template('statistics.html', stats={
            'users': {},
            'groups': {},
            'security': {},
            'activity': {}
        })
