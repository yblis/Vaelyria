from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app
from flask_login import login_user, logout_user, login_required
from ldap_utils import get_ldap_connection
from auth_models import User
from audit_log import log_user_action

bp = Blueprint('auth', __name__)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Veuillez remplir tous les champs', 'warning')
            return render_template('auth/login.html')

        try:
            # Test de connexion LDAP avec les identifiants fournis
            conn = get_ldap_connection(username, password)
            if conn.bound:
                # Vérifier si un groupe autorisé est configuré
                authorized_group = current_app.config.get('AUTHORIZED_AD_GROUP')
                
                if authorized_group:
                    # Rechercher le DN de l'utilisateur
                    base_dn = current_app.config['BASE_DN']
                    user_filter = f'(&(objectClass=user)(sAMAccountName={username}))'
                    conn.search(base_dn, user_filter, attributes=['memberOf'])
                    
                    if not conn.entries:
                        flash('Utilisateur non trouvé', 'warning')
                        log_user_action('Failed Login', f'User {username} not found in AD')
                        return render_template('auth/login.html')
                    
                    user_groups = [g.lower() for g in conn.entries[0].memberOf.values]
                    if not any(authorized_group.lower() in group.lower() for group in user_groups):
                        flash('Accès non autorisé', 'warning')
                        log_user_action('Failed Login', f'User {username} not in authorized group')
                        return render_template('auth/login.html')

                user = User(1, username)  # ID fixe car nous utilisons l'auth LDAP
                login_user(user)
                # Stocker les identifiants LDAP dans la session
                session['ldap_user'] = username
                session['ldap_password'] = password
                log_user_action('Login', f'User {username} logged in successfully')
                return redirect(url_for('users.dashboard'))
            else:
                flash('Identifiants incorrects', 'warning')
                log_user_action('Failed Login', f'Failed login attempt for user {username}')

        except Exception as e:
            flash('Erreur de connexion', 'danger')
            log_user_action('Login Error', f'Login error: {str(e)}')

    return render_template('auth/login.html')

@bp.route('/logout')
@login_required
def logout():
    # Nettoyer les identifiants LDAP de la session
    session.pop('ldap_user', None)
    session.pop('ldap_password', None)
    logout_user()
    flash('Vous avez été déconnecté', 'info')
    return redirect(url_for('auth.login'))
