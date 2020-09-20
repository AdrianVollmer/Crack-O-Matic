"""Here the server-less mode is tested"""

import os
import sys
import json
import tempfile
import logging

#  import pytest


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_PATH, '..'))


def test_serverless(global_data, caplog):
    from crackomatic.audit import get_audit_sample,\
            perform_audit, DEFAULTS
    from common import cracker_config, email_config, audit_config
    config = get_audit_sample()
    cracker_config = cracker_config(global_data)
    audit_config = audit_config(global_data)

    del email_config['section']
    del cracker_config['section']

    for k, v in audit_config.items():
        assert k in config['audit'] or k in DEFAULTS
        config['audit'][k] = v
    for k, v in email_config.items():
        assert k in config['email'] or k in DEFAULTS
        config['email'][k] = v
    for k, v in cracker_config.items():
        assert k in config['cracker'] or k in DEFAULTS
        config['cracker'][k] = v

    caplog.set_level(logging.DEBUG)
    caplog.clear()
    with tempfile.NamedTemporaryFile(mode='w') as audit_file:
        json.dump(config, audit_file)
        audit_file.flush()
        perform_audit(audit_file.name)
    print(caplog.text)
    assert 'FINISHED' in caplog.text
