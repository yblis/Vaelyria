from flask import Flask, redirect, url_for, send_from_directory, request, session
from flask_login import login_required, current_user
from flask_babel import Babel, _, get_locale
from routes import auth, users, groups, export, service_profiles, api, settings, logs, language, ou
from audit_log import setup_audit_logging
from models import db, LDAPConfig
from auth_models import User
from flask_login import LoginManager
from dotenv import load_dotenv
from ldap_utils import init_service_profiles_db
from flask_apscheduler import APScheduler
from log_maintenance import purge_old_logs
import os

load_dotenv()

instance_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'instance'))
if not os.path.exists(instance_path):
    os.makedirs(instance_path)

# Initialize Flask app
app = Flask(__name__)

# Basic configuration
app.config.update(
    SECRET_KEY=os.getenv('FLASK_SECRET_KEY'),
    BABEL_DEFAULT_LOCALE='fr',
    BABEL_LANGUAGES=['fr', 'en'],
    BABEL_TRANSLATION_DIRECTORIES='translations',
    LANGUAGES=['fr', 'en']  # Available languages
)

# Initialize Babel
babel = Babel(app)

def get_locale():
    """Return the best matched language for the current user."""
    # Try to get language from session
    if 'language' in session:
        return session['language']
    # Try to get language from user preferences (if logged in)
    if current_user.is_authenticated and hasattr(current_user, 'language'):
        return current_user.language
    # Fallback to browser's preferred language or default to French
    return request.accept_languages.best_match(app.config['LANGUAGES']) or 'fr'

babel.init_app(app, locale_selector=get_locale)

# Configure Jinja2 for i18n
app.jinja_env.add_extension('jinja2.ext.i18n')
app.jinja_env.globals['get_locale'] = get_locale
app.jinja_env.globals['_'] = _

# Make translations available in templates
@app.context_processor
def inject_conf_var():
    return dict(
        LANGUAGES=app.config['LANGUAGES'],
        CURRENT_LANGUAGE=get_locale()
    )

# Configuration de la rétention des logs
LOG_RETENTION_MONTH = int(os.getenv('LOG_RETENTION_MONTH', 12))
if LOG_RETENTION_MONTH < 1:
    LOG_RETENTION_MONTH = 1
app.config['LOG_RETENTION_MONTH'] = LOG_RETENTION_MONTH
app.config['PURGE_RUNNING'] = False

# Initialisation du scheduler
scheduler = APScheduler()
scheduler.init_app(app)
app.config['SCHEDULER_API_ENABLED'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(instance_path, "ldap_config.db")}'
app.config['SQLALCHEMY_BINDS'] = {
    'service_profiles': f'sqlite:///{os.path.join(instance_path, "service_profiles.db")}'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

# Configuration du scheduler pour la purge des logs
scheduler.add_job(
    id='purge_logs',
    func=purge_old_logs,
    args=[app],
    trigger='cron',
    hour=2,  # Exécution à 2h du matin
    minute=0
)
scheduler.start()

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# Initialize database and load LDAP config
with app.app_context():
    db.create_all()
    # Configuration LDAP
    app.config.update(
        LDAP_SERVER=os.getenv('LDAP_SERVER'),
        BASE_DN=os.getenv('BASE_DN'),
        LDAP_DOMAIN=os.getenv('LDAP_DOMAIN', ''),
        LDAP_PORT=int(os.getenv('LDAP_PORT', 389)),
        LDAP_USE_SSL=os.getenv('LDAP_USE_SSL', '').lower() in ('true', '1', 'yes', 'on'),
        AUTHORIZED_AD_GROUP=os.getenv('AUTHORIZED_AD_GROUP', '')
    )

    # Récupérer l'OU Corbeille depuis la base de données
    config = LDAPConfig.get_config()
    if config:
        app.config['TRASH_OU'] = config.trash_ou
    else:
        app.config['TRASH_OU'] = ''
    
    # Initialize service profiles database
    init_service_profiles_db()

# Set up audit logging
setup_audit_logging(app)

# Register blueprints
app.register_blueprint(auth.bp, url_prefix='/auth')
app.register_blueprint(users.bp, url_prefix='/users')
app.register_blueprint(groups.bp, url_prefix='/groups')
app.register_blueprint(export.bp, url_prefix='/export')
app.register_blueprint(service_profiles.service_profiles_bp, url_prefix='/settings/service_profiles')
app.register_blueprint(settings.bp, url_prefix='/settings')
app.register_blueprint(api.bp)
app.register_blueprint(logs.bp, url_prefix='/logs')
app.register_blueprint(language.bp)
app.register_blueprint(ou.bp, url_prefix='/settings')

# Add root URL rule to redirect to users.dashboard
@app.route('/')
@login_required
def index():
    return redirect(url_for('users.dashboard'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
