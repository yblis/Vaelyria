from flask import Blueprint, jsonify, request
from ldap_utils import (
    get_ldap_connection, get_user_statistics, get_group_statistics,
    get_security_statistics, get_activity_statistics
)
from audit_log import log_user_action
from ldap3 import SUBTREE
from os import getenv

bp = Blueprint('api', __name__, url_prefix='/api')

def build_ou_tree(entries, current_dn=None):
    """Construit une structure arborescente des OUs de manière récursive"""
    if current_dn is None:
        current_dn = getenv('BASE_DN')

    # Filtrer les entrées qui sont des enfants directs du DN actuel
    children = [
        entry for entry in entries 
        if (
            entry.entry_dn.endswith(',' + current_dn) and 
            len(entry.entry_dn.split(',')) == len(current_dn.split(',')) + 1
        )
    ]

    # Construire un nœud pour chaque enfant
    nodes = []
    for child in children:
        node = {
            'name': child.name.value if hasattr(child, 'name') else child.entry_dn.split(',')[0].split('=')[1],
            'dn': child.entry_dn,
            'children': build_ou_tree(entries, child.entry_dn)
        }
        nodes.append(node)

    # Trier les nœuds par nom
    return sorted(nodes, key=lambda x: x['name'])

@bp.route('/statistics')
def get_statistics():
    """API endpoint pour récupérer toutes les statistiques"""
    try:
        conn = get_ldap_connection()
        stats = {
            'users': get_user_statistics(conn),
            'groups': get_group_statistics(conn),
            'security': get_security_statistics(conn),
            'activity': get_activity_statistics(conn)
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ldap/ou/create', methods=['POST'])
def create_ou():
    """Create a new Organizational Unit"""
    try:
        data = request.get_json()
        parent_dn = data.get('parent_dn')
        ou_name = data.get('name')
        
        if not parent_dn or not ou_name:
            return jsonify({'error': 'Parent DN and OU name are required'}), 400
        
        conn = get_ldap_connection()
        ou_dn = f"OU={ou_name},{parent_dn}"
        
        # Check if OU already exists
        conn.search(ou_dn, '(objectClass=*)', SUBTREE, attributes=['*'])
        if len(conn.entries) > 0:
            return jsonify({'error': 'OU already exists'}), 409
            
        # Create the new OU
        result = conn.add(ou_dn, ['organizationalUnit', 'top'], {'ou': ou_name})
        
        if not result:
            log_user_action('OU_CREATE_FAILED', f'Failed to create OU: {ou_dn}', level='ERROR')
            return jsonify({'error': conn.result['description']}), 500
            
        log_user_action('OU_CREATE', f'Created new OU: {ou_dn}')
        return jsonify({'message': 'OU created successfully', 'dn': ou_dn}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ldap/ou/<path:dn>', methods=['DELETE'])
def delete_ou(dn):
    """Delete an Organizational Unit"""
    try:
        conn = get_ldap_connection()
        
        # Check if OU exists and is empty
        conn.search(dn, '(objectClass=*)', SUBTREE, attributes=['*'])
        if len(conn.entries) > 1:  # More than 1 means it has children
            return jsonify({'error': 'Cannot delete OU with child objects'}), 400
            
        # Delete the OU
        result = conn.delete(dn)
        
        if not result:
            log_user_action('OU_DELETE_FAILED', f'Failed to delete OU: {dn}', level='ERROR')
            return jsonify({'error': conn.result['description']}), 500
            
        log_user_action('OU_DELETE', f'Deleted OU: {dn}')
        return jsonify({'message': 'OU deleted successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ldap/ou/<path:dn>', methods=['PUT'])
def update_ou(dn):
    """Rename or move an Organizational Unit"""
    try:
        data = request.get_json()
        new_name = data.get('new_name')
        new_parent_dn = data.get('new_parent_dn')
        
        if not new_name and not new_parent_dn:
            return jsonify({'error': 'New name or parent DN is required'}), 400
            
        conn = get_ldap_connection()
        
        # Handle renaming
        if new_name:
            new_rdn = f"OU={new_name}"
            result = conn.modify_dn(dn, new_rdn, new_superior=new_parent_dn)
            
            if not result:
                log_user_action('OU_RENAME_FAILED', f'Failed to rename OU: {dn} to {new_name}', level='ERROR')
                return jsonify({'error': conn.result['description']}), 500
            
            log_user_action('OU_RENAME', f'Renamed OU: {dn} to {new_name}')
            
        return jsonify({'message': 'OU updated successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/ldap/ou_tree')
def get_ou_tree():
    """API endpoint pour récupérer l'arborescence des OUs"""
    try:
        conn = get_ldap_connection()
        
        # Rechercher toutes les OUs
        conn.search(getenv('BASE_DN'), 
                   '(objectClass=organizationalUnit)', 
                   attributes=['name'])
        
        # Construire l'arborescence
        root = {
            'name': getenv('BASE_DN').split(',')[0].split('=')[1],
            'dn': getenv('BASE_DN'),
            'children': build_ou_tree(conn.entries)
        }
        
        return jsonify(root)
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@bp.route('/users/search')
def search_users():
    """API endpoint pour rechercher des utilisateurs par nom/prénom"""
    try:
        query = request.args.get('q', '').strip()
        if not query or len(query) < 2:
            return jsonify([])

        conn = get_ldap_connection()
        
        # Rechercher les utilisateurs dont le nom ou prénom contient la chaîne de recherche
        search_filter = f'(&(objectClass=user)(|(cn=*{query}*)(givenName=*{query}*)(sn=*{query}*))(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
        
        conn.search(getenv('BASE_DN'), 
                   search_filter,
                   attributes=['cn', 'givenName', 'sn', 'distinguishedName'])
        
        results = []
        for entry in conn.entries:
            results.append({
                'displayName': f"{entry.sn.value if hasattr(entry, 'sn') else ''}, {entry.givenName.value if hasattr(entry, 'givenName') else ''}".strip(', '),
                'dn': entry.entry_dn
            })
        
        return jsonify(results)
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500
