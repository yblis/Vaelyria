from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ldap_utils import (create_service_profile, get_service_profiles, update_service_profile, 
                       delete_service_profile, get_ldap_connection, get_service_profile, apply_profile_to_existing_users)
from os import getenv
from models import db, ServiceProfile

service_profiles_bp = Blueprint('service_profiles', __name__, url_prefix='/settings/service_profiles')

@service_profiles_bp.route('/', methods=['GET'])
def list_profiles():
    profiles = get_service_profiles()
    return render_template('service_profiles_list.html', profiles=profiles)

@service_profiles_bp.route('/create', methods=['GET','POST'])
def create_profile():
    if request.method == 'POST':
        print("Debug - Form data:", dict(request.form))
        name = request.form.get('name')
        ou = request.form.get('ou')
        groups = request.form.getlist('groups')
        extras = request.form.get('extras', '')
        manager = request.form.get('manager')
        function = request.form.get('function')
        service = request.form.get('service')
        society = request.form.get('society')
        ip_telephony = 'ip_telephony' in request.form
        
        domain = request.form.get('domains')
        domains = [domain] if domain else []
        print("Debug - Form domain:", domain)
        # Récupérer les suffixes
        samaccountname_suffix = request.form.get('samaccountname_suffix')
        commonname_suffix = request.form.get('commonname_suffix')
        givenname_suffix = request.form.get('givenname_suffix')
        mail_suffix = request.form.get('mail_suffix')
        mailnickname_suffix = request.form.get('mailnickname_suffix')
        proxyaddresses_suffix = request.form.get('proxyaddresses_suffix')
        targetaddress_suffix = request.form.get('targetaddress_suffix')

        create_service_profile(
            name, ou, groups, extras, manager, domains,
            function=function, service=service, society=society,
            ip_telephony=ip_telephony,
            samaccountname_suffix=samaccountname_suffix,
            commonname_suffix=commonname_suffix,
            givenname_suffix=givenname_suffix,
            mail_suffix=mail_suffix,
            mailnickname_suffix=mailnickname_suffix,
            proxyaddresses_suffix=proxyaddresses_suffix,
            targetaddress_suffix=targetaddress_suffix
        )
        return redirect(url_for('service_profiles.list_profiles'))
    # Récupérer la liste des OUs et des groupes
    conn = get_ldap_connection()
    
    # Rechercher les OUs
    conn.search(getenv('BASE_DN'), '(objectClass=organizationalUnit)', attributes=['distinguishedName', 'name'])
    available_ous = [{'dn': entry.distinguishedName.value, 'name': entry.name.value} 
                     for entry in conn.entries if hasattr(entry, 'name')]

    # Rechercher les groupes
    conn.search(getenv('BASE_DN'), '(objectClass=group)', attributes=['distinguishedName', 'name'])
    available_groups = [{'dn': entry.distinguishedName.value, 'name': entry.name.value} 
                       for entry in conn.entries if hasattr(entry, 'name')]

    # Rechercher les utilisateurs pour la liste des managers
    conn.search(getenv('BASE_DN'), '(objectClass=user)', attributes=['distinguishedName', 'displayName'])
    available_managers = [{'dn': entry.distinguishedName.value, 'name': entry.displayName.value} 
                       for entry in conn.entries if hasattr(entry, 'displayName')]

    # Récupérer les domaines depuis la configuration LDAP
    ldap_config = LDAPConfig.get_config()
    available_domains = ldap_config.domains.split('\n') if ldap_config and ldap_config.domains else []

    return render_template('service_profiles_create.html', 
                         available_ous=available_ous,
                         available_groups=available_groups,
                         available_managers=available_managers,
                         available_domains=available_domains)

from models import LDAPConfig
import json

@service_profiles_bp.route('/edit/<int:profile_id>', methods=['GET','POST'])
def edit_profile(profile_id):
    if request.method == 'POST':
        print("Debug - Form data:", dict(request.form))
        name = request.form.get('name')
        ou = request.form.get('ou')
        groups = request.form.getlist('groups')
        extras = request.form.get('extras', '')
        manager = request.form.get('manager')
        function = request.form.get('function')
        service = request.form.get('service')
        society = request.form.get('society')
        ip_telephony = 'ip_telephony' in request.form
        
        domains = [request.form.get('domains')] if request.form.get('domains') else []
        print("Debug - Form domain:", domains[0] if domains else None)
        # Récupérer les suffixes
        samaccountname_suffix = request.form.get('samaccountname_suffix')
        commonname_suffix = request.form.get('commonname_suffix')
        givenname_suffix = request.form.get('givenname_suffix')
        mail_suffix = request.form.get('mail_suffix')
        mailnickname_suffix = request.form.get('mailnickname_suffix')
        proxyaddresses_suffix = request.form.get('proxyaddresses_suffix')
        targetaddress_suffix = request.form.get('targetaddress_suffix')

        update_service_profile(
            profile_id, name, ou, groups, extras, manager, domains,
            function=function, service=service, society=society,
            ip_telephony=ip_telephony,
            samaccountname_suffix=samaccountname_suffix,
            commonname_suffix=commonname_suffix,
            givenname_suffix=givenname_suffix,
            mail_suffix=mail_suffix,
            mailnickname_suffix=mailnickname_suffix,
            proxyaddresses_suffix=proxyaddresses_suffix,
            targetaddress_suffix=targetaddress_suffix
        )
        return redirect(url_for('service_profiles.list_profiles'))
    
    conn = get_ldap_connection()
    
    # Récupérer le profil existant
    print("Debug - Edit GET - Loading profile")
    profile = get_service_profile(profile_id)
    if not profile:
        flash('Profil non trouvé', 'warning')
        return redirect(url_for('service_profiles.list_profiles'))
    print("Debug - Edit GET - Profile data:", {
        'manager': profile.manager,
        'domains': profile.domains
    })

    # Récupérer les OUs
    conn.search(getenv('BASE_DN'), '(objectClass=organizationalUnit)', attributes=['distinguishedName', 'name'])
    available_ous = [{'dn': entry.distinguishedName.value, 'name': entry.name.value} 
                     for entry in conn.entries if hasattr(entry, 'name')]

    # Récupérer les groupes
    conn.search(getenv('BASE_DN'), '(objectClass=group)', attributes=['distinguishedName', 'name'])
    available_groups = [{'dn': entry.distinguishedName.value, 'name': entry.name.value} 
                       for entry in conn.entries if hasattr(entry, 'name')]

    # Rechercher les utilisateurs pour la liste des managers
    conn.search(getenv('BASE_DN'), '(objectClass=user)', attributes=['distinguishedName', 'displayName'])
    available_managers = [{'dn': entry.distinguishedName.value, 'name': entry.displayName.value} 
                       for entry in conn.entries if hasattr(entry, 'displayName')]

    # Récupérer les domaines depuis la configuration LDAP
    config = LDAPConfig.get_config()
    available_domains = [d.strip() for d in config.domains.split('\n') if d.strip()] if config and config.domains else []
    
    # Récupérer les domaines du profil
    profile_domains = profile.domains if profile.domains else []

    return render_template('service_profiles_edit.html', 
                         profile=profile,
                         available_ous=available_ous,
                         available_groups=available_groups,
                         available_managers=available_managers,
                         available_domains=available_domains,
                         profile_domains=profile_domains)

@service_profiles_bp.route('/delete/<int:profile_id>', methods=['POST'])
def remove_profile(profile_id):
    delete_service_profile(profile_id)
    return redirect(url_for('service_profiles.list_profiles'))

@service_profiles_bp.route('/get_profile/<int:profile_id>')
def get_profile(profile_id):
    """Récupère les détails d'un profil au format JSON"""
    profile = get_service_profile(profile_id)
    if not profile:
        return jsonify({'error': 'Profile not found'}), 404
    
    return jsonify({
        'id': profile.id,
        'name': profile.name,
        'ou': profile.ou,
        'groups': profile.groups,
        'extras': profile.extras,
        'function': profile.function,
        'service': profile.service,
        'society': profile.society,
        'ip_telephony': profile.ip_telephony,
        'samaccountname_suffix': profile.samaccountname_suffix,
        'commonname_suffix': profile.commonname_suffix,
        'givenname_suffix': profile.givenname_suffix,
        'mail_suffix': profile.mail_suffix,
        'mailnickname_suffix': profile.mailnickname_suffix,
        'proxyaddresses_suffix': profile.proxyaddresses_suffix,
        'targetaddress_suffix': profile.targetaddress_suffix
    })

@service_profiles_bp.route('/duplicate/<int:profile_id>', methods=['POST'])
def duplicate_profile(profile_id):
    """Duplique un profil de service existant"""
    profile = get_service_profile(profile_id)
    if not profile:
        flash('Profil non trouvé', 'warning')
        return redirect(url_for('service_profiles.list_profiles'))
    
    # Créer un nouveau profil avec les mêmes paramètres
    create_service_profile(
        name=f"{profile.name} (Copie)",
        ou=profile.ou,
        groups=profile.groups,
        extras=profile.extras,
        manager=profile.manager,
        domains=profile.domains if isinstance(profile.domains, list) else [],
        function=profile.function,
        service=profile.service,
        society=profile.society,
        ip_telephony=profile.ip_telephony,
        samaccountname_suffix=profile.samaccountname_suffix,
        commonname_suffix=profile.commonname_suffix,
        givenname_suffix=profile.givenname_suffix,
        mail_suffix=profile.mail_suffix,
        mailnickname_suffix=profile.mailnickname_suffix,
        proxyaddresses_suffix=profile.proxyaddresses_suffix,
        targetaddress_suffix=profile.targetaddress_suffix
    )
    
    flash('Profil dupliqué avec succès', 'success')
    return redirect(url_for('service_profiles.list_profiles'))

@service_profiles_bp.route('/apply_to_existing/<int:profile_id>', methods=['POST'])
def apply_to_existing(profile_id):
    """Applique les paramètres d'un profil aux utilisateurs existants"""
    try:
        result = apply_profile_to_existing_users(profile_id)
        if result:
            return jsonify({'success': True})
        return jsonify({'error': 'Failed to apply profile'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@service_profiles_bp.route('/reorder', methods=['POST'])
def reorder_profiles():
    """Update the order of service profiles"""
    order = request.json.get('order', [])
    try:
        for item in order:
            profile = ServiceProfile.query.get(item['id'])
            if profile:
                profile.order = item['position']
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})
