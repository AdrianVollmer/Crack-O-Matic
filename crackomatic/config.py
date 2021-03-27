import json

from wtforms import HiddenField
from flask_wtf import FlaskForm
import wtforms
from wtforms.validators import DataRequired


cracker_fields = [
    wtforms.SelectField(
        "Cracker",
        choices=[("John", "John"), ("Hashcat", "Hashcat")],
        # wtforms 2.2 requires a list of tuples
        # https://github.com/wtforms/wtforms/pull/526
        description={
            'id': 'cracker',
            'help': "Choose 'John' or 'Hashcat'",
        }
    ),
    wtforms.StringField(
        "Binary Path",
        description={
            'help': "Path to the binary",
            'placeholder': "/usr/sbin/john",
            'id': 'binary_path',
        },
        validators=[DataRequired("This field is required.")],
    ),
    wtforms.StringField(
        "Wordlist Path",
        description={
            'help': "Path to the wordlist (we recommend <a href='https://crackstation.net/crackstation-wordlist-password-cracking-dictionary.htm'>Crackstation's wordlist</a>)", # noqa
            'placeholder': "/usr/share/seclists/Passwords/openwall.net-all.txt",  # noqa
            'id': 'wordlist_path',
        },
        validators=[DataRequired()],
    ),
    wtforms.StringField(
        "Rule Path",
        description=dict(
            id='rule_path',
            help="Path to the rule file (we recommend <a href='https://github.com/NotSoSecure/password_cracking_rules'>OneRule</a> or <a href='https://github.com/SpiderLabs/KoreLogic-Rules'>KoreLogic</a>)", # noqa
            placeholder="/usr/share/hashcat/rules/OneRule.rule",
        ),
    ),
]


email_fields = [
    wtforms.StringField(
        "SMPT Host",
        description=dict(
            id='smtphost',
            help="Hostname of an SMTP server",
            placeholder="exch01.ad.contoso.com",
        ),
        validators=[DataRequired()],
    ),
    # SMTP Port should be IntegerField, but for whatever reason, wtforms
    # does not validate any integer as an actual integer
    wtforms.StringField(
        "SMPT Port",
        description=dict(
            id='smtpport',
            help="Port of an SMTP service",
            placeholder="465",
        ),
        validators=[DataRequired()],
    ),
    wtforms.BooleanField(
        "Use TLS",
        description=dict(
            id='smtptls',
            help="Whether to use TLS; note that you need the corresponding "
                 "CA installed on the system or specify a CA file",
        ),
    ),
    wtforms.StringField(
        "SMPT CA file",
        description=dict(
            id='smtp_cafile',
            help="Path to a CA file in PEM format",
            placeholder="/etc/ssl/Contoso-Root-CA.pem",
        ),
    ),
    wtforms.StringField(
        "Username",
        description=dict(
            id='smtpuser',
            help="Username for SMTP authentication (should be low privilege)",
        ),
    ),
    wtforms.PasswordField(
        "Password",
        description=dict(
            id='smtppass',
            help="Password for SMTP authentication",
        ),
    ),
    wtforms.StringField(
        "Sender Address",
        description=dict(
            id='smtpsender',
            help="This will be used in the 'From' field of outgoing mails",
            placeholder="crackomatic@contoso.local",
        ),
        validators=[DataRequired()],
    ),
]


authentication_fields = [
    wtforms.StringField(
        "LDAP URL",
        description=dict(
            id='ldap_url',
            help="How to access the directory (use FQDN)",
            placeholder="ldaps://dc01.contoso.local:636",
        ),
    ),
    wtforms.StringField(
        "CA File",
        description=dict(
            id='ca_file',
            help="Path to a file containing a CA certificate in PEM format"
            " that can authenticate the LDAP host",
            placeholder="/etc/ssl/certs/contoso_ROOT_CA.pem",
        ),
    ),
    wtforms.StringField(
        "Bind DN",
        description=dict(
            id='binddn',
            help="A template to use as the user's DN "
            "(replace the login ID with %s)",
            placeholder="CN=%s,CN=Users,DC=contoso,DC=local",
        ),
    ),
    wtforms.StringField(
        "Search Base DN",
        description=dict(
            id='binddn',
            help="The base DN under which to perform the search",
            placeholder="CN=Users,DC=contoso,DC=local",
        ),
    ),
    wtforms.StringField(
        "LDAP Filter",
        description=dict(
            id='filter',
            help="This defines who is allowed to log in to Crack-O-Matic",
            placeholder="(&(objectClass=user)"
            "(memberof=CN=CrackomaticAdmins,CN=Users,DC=contoso,DC=local))",
        ),
    ),
]


fields = {
    'cracker': cracker_fields,
    'email': email_fields,
    'authentication': authentication_fields,
}

sections = [
    ['cracker', "Cracker"],
    ['email', "Email"],
    ['authentication', "Authentication"],
]


class CrackomaticConfig(object):
    def __init__(self, config):
        self._config = config

    def __getitem__(self, key):
        try:
            return self._config[key]
        except KeyError:
            return None

    def from_json(self, j):
        self._config = json.loads(j)

    def to_json(self):
        return json.dumps(self._config)

    def get_sections(self):
        return sections

    def get_errors(self):
        result = {}
        for section in sections:
            id = section[0]
            form = self.get_form(id)
            form.validate()
            # Ignore CSRF error
            csrf = len([1 for f in form
                        if 'csrf_token' == f.name and f.errors])
            result[id] = len(form.errors) - csrf
        return result

    def get_form(self, section):
        class TempForm(FlaskForm):
            section = HiddenField('section')

        data = {}
        for field in fields.get(section, []):
            id = field.kwargs['description']['id']
            setattr(TempForm, id, field)
            data[id] = self._config.get(section, {}).get(id, "")
        return TempForm(section=section, **data)

    def update(self, section, dct):
        try:
            self._config[section].update(dct)
        except KeyError:
            self._config[section] = dct
