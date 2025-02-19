from flask import Blueprint, render_template, request, flash, redirect, url_for
from models import db, LDAPConfig
from flask_login import login_required
from cryptography.fernet import Fernet
from base64 import b64encode
import os

bp = Blueprint('settings', __name__)

@bp.route('/ldap', methods=['GET', 'POST'])
@login_required
def ldap_settings():
    config = LDAPConfig.get_config()
    
    if request.method == 'POST':
        # Get form data
        trash_ou = request.form.get('trash_ou')
        default_password = request.form.get('default_password')
        domains = request.form.get('domains')
        tenant = request.form.get('tenant')
        
        # Get username pattern configuration
        username_pattern_order = request.form.get('username_pattern_order')
        username_first_part_chars = request.form.get('username_first_part_chars')
        username_second_part_chars = request.form.get('username_second_part_chars')
        username_separator = request.form.get('username_separator', '')
        
        # Get email pattern configuration
        email_pattern_order = request.form.get('email_pattern_order')
        email_first_part_chars = request.form.get('email_first_part_chars')
        email_second_part_chars = request.form.get('email_second_part_chars')
        email_separator = request.form.get('email_separator', '')
        
        if not trash_ou:
            flash('Le champ OU Corbeille est obligatoire.', 'warning')
        else:
            if config:
                # Update basic settings
                config.trash_ou = trash_ou
                config.domains = domains
                config.tenant = tenant
                # Update password only if a new one is provided
                if default_password and default_password.strip():
                    config.set_password(default_password)
                
                # Update username pattern settings
                config.username_pattern_order = username_pattern_order
                config.username_first_part_chars = username_first_part_chars
                config.username_second_part_chars = username_second_part_chars
                config.username_separator = username_separator
                
                # Update email pattern settings
                config.email_pattern_order = email_pattern_order
                config.email_first_part_chars = email_first_part_chars
                config.email_second_part_chars = email_second_part_chars
                config.email_separator = email_separator
            else:
                # Create new configuration
                config = LDAPConfig(
                    trash_ou=trash_ou,
                    default_password=default_password if default_password and default_password.strip() else None,
                    domains=domains,
                    tenant=tenant
                )
                # Set username pattern settings
                config.username_pattern_order = username_pattern_order
                config.username_first_part_chars = username_first_part_chars
                config.username_second_part_chars = username_second_part_chars
                config.username_separator = username_separator
                
                # Set email pattern settings
                config.email_pattern_order = email_pattern_order
                config.email_first_part_chars = email_first_part_chars
                config.email_second_part_chars = email_second_part_chars
                config.email_separator = email_separator
                db.session.add(config)
            
            try:
                db.session.commit()
                flash('Configuration LDAP mise à jour avec succès.', 'success')
                return redirect(url_for('settings.ldap_settings'))
            except Exception as e:
                db.session.rollback()
                flash(f'Erreur lors de la mise à jour: {str(e)}', 'danger')
    
    return render_template('settings/ldap.html', config=config)
