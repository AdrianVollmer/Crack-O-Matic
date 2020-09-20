from datetime import datetime as dt, timedelta
import os
import sys
import time

import pytest


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_PATH, '..'))


@pytest.fixture()
def backend(monkeypatch, global_data):
    from crackomatic.models import init_db
    init_db(global_data['DB'])
    from crackomatic.log import init_log
    init_log('DEBUG')
    from crackomatic.backend import Backend
    backend = Backend()

    def get_errors():
        """Skip error check because it requires a flask context"""
        return {}
    monkeypatch.setattr(backend.config, 'get_errors', get_errors)

    from crackomatic.job import Job

    from common import mock_run
    monkeypatch.setattr(Job, 'run', mock_run)

    yield backend
    backend.clean_up()


def test_scheduler(backend, global_data):
    from crackomatic.constants import AuditState, AuditFrequency
    config = dict(
        cracker=dict(
            cracker='John',
            binary_path=global_data['JOHN_PATH'],
            wordlist_path=global_data['WORDLIST'],
            rule_path='best64',
            section='cracker',
        ),
        email=dict(
            smtpport=456,
            section='email',
        ),
        authentication=dict(
            test='one',
            section='authentication',
        ),
    )
    in_ten_seconds = dt.now() + timedelta(seconds=10)
    in_ten_seconds = in_ten_seconds.strftime("%Y-%m-%d %H:%M:%S")
    values = {
        'user': 'foo',
        'domain': 'foo',
        'password': 'foo',
        'email_field': '',
        'ldap_url': 'ldaps://foo',
        'ca_file': '/etc/ssl/certs/foo.pem',
        'user_filter': '',
        'admin_filter': '',
        'message': '',
        'subject': '',
        'include_cracked': 'y',
        'start': in_ten_seconds,
        'frequency': str(int(AuditFrequency.DAILY)),
    }
    backend.config._config = config
    backend.add_audit(values)
    time.sleep(2)
    scheduled = backend.get_scheduled_audits()
    assert len(scheduled) == 1
    assert scheduled[0].state == AuditState.SCHEDULED
    time.sleep(2)
    scheduled = backend.get_scheduled_audits()
    assert len(scheduled) == 1
    assert scheduled[0].state == AuditState.SCHEDULED
    time.sleep(7)
    # Running
    scheduled = backend.get_scheduled_audits()
    root_dir = backend._job._root_dir.name
    assert scheduled == []
    assert backend._job
    assert int(backend._job.audit.state) > 1
    backend._job.wait_until_finished()
    # Check rescheduling
    time.sleep(2)
    scheduled = backend.get_scheduled_audits()
    assert len(scheduled) == 1
    assert scheduled[0].state == AuditState.SCHEDULED
    assert (
        abs(scheduled[0].start - timedelta(hours=24) - dt.now())
        < timedelta(hours=0.6)
    )
    # assert that files are gone
    assert not os.path.isdir(root_dir)
