from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, HiddenField, \
        DateTimeField, SelectField, TextAreaField
from wtforms.validators import DataRequired, Optional

from .constants import AuditFrequency


class LoginForm(FlaskForm):
    user = StringField('user', validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired()])
    remember_me = BooleanField('remember_me')
    next_url = HiddenField('next')


class NewAuditForm(FlaskForm):
    domain = StringField(
        "Domain",
        validators=[DataRequired()],
        description=dict(
            help="FQDN of the domain to be audited",
        ),
    )
    user = StringField(
        "User",
        validators=[DataRequired()],
        description=dict(
            help="Name of an account with the permission 'Replicating Directory Changes'",  # noqa
        ),
    )
    password = PasswordField(
        "Password",
        description=dict(
            help="Password of the account",
        ),
        validators=[DataRequired()],
    )
    start = DateTimeField(
        "Start at",
        format='%Y-%m-%d %H:%M:%S',
        description=dict(
            placeholder="YYYY-MM-DD HH:mm:ss",
            help="Leave empty for 'right now'",
        ),
        validators=[Optional()],
    )
    frequency = SelectField(
        "Frequency",
        choices=[
            (int(AuditFrequency.JUST_ONCE), "Just once"),
            (int(AuditFrequency.DAILY), "Daily"),
            (int(AuditFrequency.WEEKLY), "Weekly"),
            (int(AuditFrequency.MONTHLY), "Monthly"),
            (int(AuditFrequency.QUARTERLY), "Quarteryl"),
            (int(AuditFrequency.YEARLY), "Yearly"),
        ],
        validators=[DataRequired()],
        description=dict(
            help="Note: the password will be stored on disk unless the audit is run 'Just once'",  # noqa
        ),
    )
    dc_ip = StringField(
        "DC IP",
        description=dict(
            id='dc_ip',
            help="Optional IP address of the DC to use for replication",
            placeholder="10.10.10.10",
        ),
    )
    ldap_url = StringField(
        "LDAP URL",
        description=dict(
            id='ldap_url',
            help="LDAP URL of the directory (use FQDN)",
            placeholder="ldaps://dc01.contoso.local:636",
        ),
        validators=[DataRequired()],
    )
    ca_file = StringField(
        "CA File",
        description=dict(
            id='ca_file',
            help="Path to a file containing a CA certificate in PEM format"
            " that can authenticate the LDAP host",
            placeholder="/etc/ssl/certs/contoso_ROOT_CA.pem",
        ),
        validators=[DataRequired()],
    )
    email_field = StringField(
        "E-Mail field",
        description=dict(
            placeholder="mail",
            help="Name of the email attribute in LDAP",
        ),
        validators=[DataRequired()],
    )
    user_filter = StringField(
        "LDAP filter (notified users)",
        description=dict(
            placeholder="(&amp;(objectClass=person)(objectClass=user)",
            help="Only users passing this LDAP filter will be notified if"
                 " their password was cracked",
        ),
        validators=[DataRequired()],
    )
    admin_filter = StringField(
        "LDAP filter (notified admins)",
        description=dict(
            placeholder="(&amp;(objectClass=person)(objectClass=user)"
                        "(memberOf=cn=crackomaticAdmins,ou=users,"
                        "dc=company,dc=com)",
            help="Only admin users passing this LDAP filter will receive"
                 " a report",
        ),
        validators=[DataRequired()],
    )
    subject = StringField(
        "Subject",
        description=dict(
            placeholder="A message regarding your password",
            help="The subject field of the email that is sent to affected"
                 " users",
        ),
        validators=[DataRequired()],
    )
    message = TextAreaField(
        "Message",
        description=dict(
            help="The message that is sent to affected users",
        ),
    )
    include_cracked = BooleanField(
        "List cracked accounts",
        description=dict(
            help="Whether to include a list of cracked accounts in the admin"
                 " report",
        ),
    )
