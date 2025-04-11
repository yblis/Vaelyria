from flask import Blueprint, render_template
from flask_login import login_required
from flask_babel import _

bp = Blueprint('ou', __name__)

@bp.route('/settings/ou')
@login_required
def manage_ou():
    """Render the OU management page."""
    return render_template('ou/manage.html', title=_('Organization Units Management'))
