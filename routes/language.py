from flask import Blueprint, session, redirect, url_for, request, g
from flask_babel import refresh

bp = Blueprint('language', __name__)

@bp.route('/language/<lang>')
def change_language(lang):
    # Only allow supported languages
    if lang in ['fr', 'en']:
        session['language'] = lang
        # Force Babel to refresh the locale
        refresh()
    return redirect(request.referrer or url_for('index'))
