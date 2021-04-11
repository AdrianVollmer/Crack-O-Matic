from logging import getLogger
from os import urandom
from urllib.parse import urlparse, urljoin, urlencode

import flask
from flask_login import current_user, login_user, \
            logout_user, login_required, LoginManager
from babel.dates import format_datetime

from .user import User
from ._version import __version__
from .forms import LoginForm, NewAuditForm
from .backend import Backend
from .constants import AuditState, AuditFrequency

app = flask.Flask(__name__)
app.secret_key = urandom(16)
app.config.update(
    #  SESSION_COOKIE_SECURE=True,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.remember_cookie_http_only = True
login_manager.remember_cookie_samesite = True

backend = Backend()
log = getLogger(__name__)


class Pagination(object):
    def __init__(self, total_entries, page_size=5, p_name='page'):
        try:
            current_page = int(flask.request.args.get(p_name))
        except Exception:
            current_page = 1

        first_page = 1
        last_page = total_entries//page_size + 1

        if not (first_page <= current_page and current_page <= last_page):
            raise IndexError("Page index out of range")
        if first_page == last_page:
            self.needed = False
            return
        self.needed = True

        args = flask.request.args.to_dict()

        self.page = current_page
        self.first = first_page
        self.last = last_page

        self.previous = ""
        self.next = ""
        if self.page != self.first:
            args[p_name] = current_page - 1
            self.previous = "?" + urlencode(args)
        if self.page != self.last:
            args[p_name] = current_page + 1
            self.next = "?" + urlencode(args)

        self.links = []
        for i in range(first_page, last_page+1):
            args.update({p_name: i})
            url = '?' + urlencode(args)
            self.links.append({p_name: i, 'href': url})

        if len(self.links) > 7:
            if current_page - first_page < 4:
                right = max(5, current_page - first_page + 2)
                self.links = self.links[:right] + [None] + [self.links[-1]]
            elif last_page - current_page < 4:
                left = min(last_page - first_page - 4, last_page -
                           first_page - (last_page - current_page))
                self.links = [self.links[0]] + [None] + self.links[left:]
            else:
                left = current_page - first_page - 1
                right = current_page - first_page + 2
                self.links = [self.links[0]] + [None] + \
                    self.links[left:right] + \
                    [None] + [self.links[-1]]


def get_context():
    return dict(
        version=__version__,
        user=current_user.get_id(),
        config_errors=sum(backend.config.get_errors().values()),
    )


def is_safe_url(target):
    # Check if the URL belongs to our application
    ref_url = urlparse(flask.request.host_url)
    test_url = urlparse(urljoin(flask.request.host_url, target))
    return (test_url.scheme in ('http', 'https')
            and ref_url.netloc == test_url.netloc)


@login_manager.user_loader
def load_user(user_id):
    return User.logged_in_users[user_id]


@app.route('/login', methods=['POST', 'GET'])
def login():
    if current_user.is_authenticated:
        return flask.redirect(flask.url_for('home'))

    next_url = flask.request.args.get('next', "")

    form = LoginForm(next_url=next_url)
    if form.validate_on_submit():
        next_url = form.next_url.data
        # Prevent open redirection
        if not is_safe_url(next_url):
            return flask.abort(400)
        auth_config = backend.config['authentication']
        user = None
        try:
            user = User.authenticate(
                form.user.data,
                form.password.data,
                auth_config,
            )
        except Exception as e:
            log.warning(str(e))
        if not user:
            flask.flash("Invalid username or password.", 'danger')
            return flask.render_template('login.html', form=form)
        login_user(user, remember=form.remember_me.data)
        return flask.redirect(next_url or flask.url_for('home'))
    return flask.render_template('login.html', form=form)


@app.route('/')
@login_required
def home():
    status = backend.get_status()
    return flask.render_template(
        'home.html',
        sections=status,
        **get_context(),
    )


@app.route('/audit')
@login_required
def audit():
    try:
        audit_uuid = flask.request.args.get('id')
        _, audit_record = backend.get_report_and_audit(audit_uuid)

        audit = {}
        dummy_form = NewAuditForm()
        display_str = {
            'uuid': "ID",
            'end': "End at",
            'state': "State",
            'report': "Report",
        }
        for k, v in audit_record.items():
            if k in ['metadata', 'id']:
                continue
            if k == 'frequency':
                audit[k] = AuditFrequency(v).name
            elif k == 'state':
                audit[k] = AuditState(v).name
            else:
                audit[k] = v
            try:
                display_str[k] = getattr(dummy_form, k).label
            except AttributeError:
                pass
    except Exception as e:
        log.error("Error while retrieving audit: %s" % str(e))
        log.exception(e)
        return str(e), 500
    return flask.render_template(
        'audit.html',
        display_str=display_str,
        audit=audit,
        **get_context(),
    )


@app.route('/audits')
@login_required
def audits():
    try:
        page = int(flask.request.args.get('page'))
    except Exception:
        page = 1
    page_size = 5

    past_audits = backend.get_past_audits()
    pagination = Pagination(len(past_audits))
    past_audits = past_audits[(page - 1)*page_size:page*page_size]

    scheduled_audits = backend.get_scheduled_audits()
    for audit in scheduled_audits:
        audit['start'] = format_datetime(audit['start'], format='short')
        if audit['end']:
            audit['end'] = format_datetime(audit['end'], format='short')

    return flask.render_template(
        'audits.html',
        running_audit=None,
        past_audits=past_audits,
        scheduled_audits=scheduled_audits,
        pagination=pagination,
        **get_context(),
    )


@app.route('/audits/delete', methods=['POST'])
@login_required
def delete_audit():
    audit_uuid = flask.request.args.get('id')
    backend.delete_audit(audit_uuid)
    return flask.redirect(flask.url_for('audits'))


@app.route('/audits/new', methods=['POST', 'GET'])
@login_required
def new_audit():
    AUDIT_MESSAGE = """\
Dear user,

your password has been identified as too weak during a fully automated
password audit. Please change your password to a more secure one soon.

This is an automated message. No human has seen your current password.
Please contact your IT department if you have further questions.
"""
    audit_uuid = flask.request.args.get('id')
    if audit_uuid:
        _, audit = backend.get_report_and_audit(audit_uuid)
        audit['password'] = ''
        audit['start'] = ''
        form = NewAuditForm(**dict(audit))
    else:
        form = NewAuditForm(message=AUDIT_MESSAGE)
    if form.validate_on_submit():
        values = flask.request.form.copy()
        if 'csrf_token' in values:
            del values['csrf_token']
        try:
            id = backend.add_audit(values)
            log.info("User '%s' created a new audit with ID %s" %
                     (current_user.get_id(), id))
            return flask.redirect(flask.url_for('home'))
        except Exception as e:
            log.error(
                "User '%s' attempted to create a new audit, but it failed: %s"  # noqa
                % (current_user.get_id(), str(e))
            )
            log.exception(e)
            flask.flash(str(e), 'danger')
    return flask.render_template(
        'new-audit.html',
        form=form,
        **get_context(),
    )


@app.route('/events')
@login_required
def events():
    if 'flat' in flask.request.args:
        response = flask.make_response(backend.get_log(), 200)
        response.mimetype = "text/plain"
        return response
    try:
        page = int(flask.request.args.get('page'))
    except Exception:
        page = 1
    page_size = 5
    pagination = Pagination(backend.get_event_count())
    event_entries = backend.get_events((page - 1)*page_size, page*page_size)
    return flask.render_template(
        'events.html',
        events=event_entries,
        pagination=pagination,
        **get_context(),
    )


@app.route('/config', methods=['POST', 'GET'])
@login_required
def config():
    sections = backend.config.get_sections()
    section = flask.request.args.get('section') or \
        flask.request.form.get('section') or \
        sections[0][0]

    errors = backend.config.get_errors()

    form = backend.config.get_form(section)
    form.validate()
    if form.validate_on_submit():
        try:
            values = form.data
            if 'csrf_token' in values:
                del values['csrf_token']
            backend.update_config(section, values)
            section = flask.request.form.get('section')
            flask.flash("Settings updated.", 'success')
            return flask.redirect(flask.url_for('config', section=section))
        except Exception as e:
            log.error("Error while updating the config: %s" % str(e))
            log.exception(e)
            flask.flash(str(e), 'danger')
    return flask.render_template(
        'config.html',
        config=config,
        section=section,
        sections=sections,
        form=form,
        errors=errors,
        **get_context(),
    )


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return flask.redirect(flask.url_for('login'))


@app.route('/report')
@login_required
def report():
    try:
        audit_id = flask.request.args.get('id', '')
        report, audit = backend.get_report_and_audit(audit_id)
        from .reports import create_text_report, create_figures
        figures = create_figures(report)
        text_report = create_text_report(report)
    except Exception as e:
        log.error("Error while retrieving report: %s" % str(e))
        log.exception(e)
        return "Unable to retrieve report", 500
    return flask.render_template(
        'report.html',
        audit_id=audit_id,
        thisaudit=audit,
        report=text_report,
        figures=figures,
        **get_context(),
    )
