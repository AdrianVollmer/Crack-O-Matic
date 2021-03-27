import json
from packaging import version

import wtforms

from .constants import AuditFrequency
from .forms import NewAuditForm
from .config import cracker_fields, email_fields


# We need to check the version of wtforms.
# Version 2.3 expects a string, version 2.2 expects an int.
frequency_default = int(AuditFrequency.JUST_ONCE)
if version.parse(wtforms.__version__) >= version.parse('2.3.0'):
    frequency_default = str(frequency_default)


DEFAULTS = {
    'frequency': frequency_default,
    'start': "",
}


def perform_audit(audit_file, interactive=False):
    from threading import Lock
    import logging

    import flask

    from .config import CrackomaticConfig
    from .job import Job
    from .forms import NewAuditForm
    from .models import AttrDict

    log = logging.getLogger(__name__)

    # Load config file
    if not audit_file:
        log.critical("You must specify a file path")
        exit(1)

    with open(audit_file, 'r') as f:
        config_settings = json.load(f)
    cracker_config = config_settings['cracker']
    email_config = config_settings['email']
    audit = AttrDict(config_settings['audit'])
    del config_settings['audit']

    # Use WTForms to validate input.
    # WTForms requires an app context, so create a dummy app.
    app = flask.Flask(__name__)
    app.config['WTF_CSRF_ENABLED'] = False
    with app.test_request_context('/'):
        email_form = CrackomaticConfig(config_settings).get_form('email')
        cracker_form = CrackomaticConfig(config_settings).get_form('cracker')
        audit_form = NewAuditForm(**audit)

    # Replace defaults
    for k, v in DEFAULTS.items():
        for form in [email_form, cracker_form, audit_form]:
            if k in form:
                form[k].data = v
    audit.uuid = None

    # Check for errors
    if interactive:
        while True:
            error = False
            for form in [email_form, audit_form, cracker_form]:
                if not form.validate():
                    for field, msg in form.errors.items():
                        print(msg)
                        val = input("%s: " % field)
                        form[field].data = val
                    error = True
            if not error:
                break
    else:
        error = False
        for form in [email_form, audit_form, cracker_form]:
            if not form.validate():
                log.critical("Errors found in configuration: %s" % form.errors)
                error = True
        if error:
            exit(1)

    # Run Job
    lock = Lock()
    job = Job(
        audit,
        lock,
        cracker_config,
        email_config,
        password=audit.password,
    )
    job.run()
    lock.acquire()


def remove_defaults(lst):
    for section in lst:
        for k in DEFAULTS.keys():
            if k in section:
                del section[k]


def get_audit_sample():
    audit = {k: "" for k, v in NewAuditForm.__dict__.items()
             if v.__class__.__name__ == 'UnboundField'}
    email = {f.kwargs['description']['id']: ""
             for f in email_fields}
    cracker = {f.kwargs['description']['id']: ""
               for f in cracker_fields}

    remove_defaults([audit, email, cracker])
    result = {
        'audit': audit,
        'email': email,
        'cracker': cracker,
    }
    return result


def print_audit_description():

    audit = {k: v.kwargs['description']['help']
             for k, v in NewAuditForm.__dict__.items()
             if v.__class__.__name__ == 'UnboundField'}
    email = {f.kwargs['description']['id']: f.kwargs['description']['help']
             for f in email_fields}
    cracker = {f.kwargs['description']['id']: f.kwargs['description']['help']
               for f in cracker_fields}

    remove_defaults([audit, email, cracker])
    dct = {'audit': audit, 'email': email, 'cracker': cracker}
    for k, v in dct.items():
        for field, help in v.items():
            print("%s.%s: %s" % (k, field, help))
