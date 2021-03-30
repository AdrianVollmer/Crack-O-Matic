"""Here the entire interaction with the web application is tested"""

import os
import re
import sys
import time
import tempfile

import pytest


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_PATH, '..'))


# https://stackoverflow.com/a/53963978
@pytest.fixture(scope='module')
def monkeymodule():
    from _pytest.monkeypatch import MonkeyPatch
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope='module')
def client(monkeymodule):
    # Monkeypatch all interactions with other systems
    from common import mock_get_hashes, mock_ldap_query

    monkeymodule.setattr('crackomatic.job.get_hashes', mock_get_hashes)
    monkeymodule.setattr('crackomatic.job.ldap_query', mock_ldap_query)

    # Run app
    with tempfile.NamedTemporaryFile() as tmpf:
        from crackomatic.log import init_log
        init_log()
        from crackomatic.models import init_db
        init_db('sqlite:///' + tmpf.name)
        from crackomatic import flask
        # Disable CSRF
        flask.app.config['WTF_CSRF_ENABLED'] = False

        with flask.app.test_client() as client:
            from crackomatic import user
            user.User.create('admin', 'admin')

            yield client
        flask.backend.clean_up()


def login(client, username, password):
    return client.post(
        '/login',
        data=dict(
            user=username,
            password=password
        ),
        follow_redirects=True)


def logout(client):
    return client.post('/logout', follow_redirects=True)


def create_config(client, global_data):
    from common import cracker_config, email_config, auth_config
    rv = client.post(
        '/config?section=cracker',
        data=cracker_config(global_data),
    )
    assert rv.status_code == 302
    rv = client.post(
        '/config?section=email',
        data=email_config,
    )
    assert rv.status_code == 302
    rv = client.post(
        '/config?section=authentication',
        data=auth_config,
    )
    assert rv.status_code == 302


def test_empty_db(client, caplog):
    """Start with a blank database."""

    # Check DB log entry  # TODO we disabled this for tests
    #  from crackomatic import models
    #  with models.session_scope() as s:
    #      log = s.query(models.Log).first()
    #      assert "Starting up" in log.msg

    # Check unauthenticated app
    rv = client.get('/').data.decode()
    assert '<a href="/login?next=%2F">' in rv
    assert 'Redirecting...' in rv
    rv = client.get('/audits').data.decode()
    assert '<a href="/login?next=%2Faudits">' in rv
    rv = client.get('/foo').data.decode()
    assert 'The requested URL was not found' in rv

    # Create user
    from crackomatic import user
    user.User.create('admin2', 'admin2')
    assert "Created local user 'admin2'" in caplog.text

    try:
        user.User.create('admin', 'password')
        assert None
    except Exception as e:
        assert 'UNIQUE constraint failed' in str(e)

    # Test login
    rv = login(client, 'user', 'foo').data.decode()
    assert 'Invalid username or password.' in rv
    rv = login(client, 'admin', 'admin').data.decode()
    assert 'Let\'s get cracking.' in rv
    assert 'Logged in as: admin' in rv
    assert 'Time of next audit' in rv
    assert '∞' in rv

    # Logout and back in
    logout(client)
    rv = client.get('/').data.decode()
    assert '<a href="/login?next=%2F">' in rv
    rv = login(client, 'admin', 'admin').data.decode()
    assert 'Logged in as: admin' in rv

    # Test empty pages
    rv = client.get('/config').data.decode()
    assert '<select id="cracker" name="cracker">' in rv
    assert 'placeholder="/usr/sbin/john' in rv
    rv = client.get('/events').data.decode()
    assert 'Events' in rv
    rv = client.get('/audits').data.decode()
    assert 'Audits' in rv


def test_audit_fails(client, caplog, global_data):
    from common import audit_config
    audit_config = audit_config(global_data)
    login(client, 'admin', 'admin')
    # Run audit before defining config
    try:
        rv = client.post(
            '/audits/new',
            data=audit_config,
        ).data.decode()
    except Exception as e:
        assert 'Configuration has errors' in str(e)

    create_config(client, global_data)

    # Required field missing
    rv = client.get('/audits/new').data.decode()
    del audit_config['user']
    assert 'Submit' in rv
    assert 'include_cracked' in rv
    rv = client.post(
        '/audits/new',
        data=audit_config,
    ).data.decode()
    assert 'This field is required' in rv
    audit_config['user'] = 'foo'

    # Uknown field
    audit_config['DOES_NOT_EXIST'] = 'foo'
    try:
        rv = client.post(
            '/audits/new',
            data=audit_config,
        ).data.decode()
    except Exception as e:
        err = "'DOES_NOT_EXIST' is an invalid keyword argument for Audit"
        assert err in str(e)
        assert err in caplog.text
    del audit_config['DOES_NOT_EXIST']

    # Invalid date
    audit_config['start'] = 'foo'
    rv = client.post(
        '/audits/new',
        data=audit_config,
    ).data.decode()
    assert 'Not a valid datetime value' in rv
    audit_config['start'] = ''


def test_audit_success(client, caplog, global_data, mock_server):
    """Test the entire process of creating an audit in the webapp

    See if everything works, the status is updated properly, and the result
    is as expected.

    """
    from crackomatic.backend import AuditState
    from common import audit_config
    audit_config = audit_config(global_data)
    audit_config['user_filter'] = 'user'  # must match mock_ldap_query
    audit_config['admin_filter'] = 'admin'  # must not contain 'user'

    mock_server.reset()
    login(client, 'admin', 'admin')
    create_config(client, global_data)
    caplog.clear()

    # Create Audit
    rv = client.post(
        '/audits/new',
        data=audit_config,
    ).data.decode()
    assert 'Redirecting...' in rv
    assert 'href="/"' in rv

    from crackomatic import flask
    from crackomatic import models
    audits = flask.backend.get_scheduled_audits()
    job = flask.backend._job
    assert len(audits) == 1
    assert job is not None
    time.sleep(1)
    uuid = job.audit.uuid
    assert "Audit with ID %s has a new state: REPLICATING" \
        % uuid in caplog.text

    rv = client.get('/').data.decode()
    assert 'REPLICATING' in rv

    # Check status meant for home page is REPLICATING
    status = flask.backend.get_status()
    assert status[0]['title'] == 'Current'
    assert status[0]['tiles'][0]['title'] == 'Running'
    assert status[0]['tiles'][0]['subtitle'] == 'State'
    assert status[0]['tiles'][1]['title'] == 'REPLICATING'
    assert status[0]['tiles'][1]['subtitle'] == 'Stage'

    # Mock replication takes 10 seconds
    time.sleep(5)
    assert job.audit.state == AuditState.REPLICATING
    time.sleep(9)

    # Check status meant for home page is CRACKING
    status = flask.backend.get_status()
    assert status[0]['title'] == 'Current'
    assert status[0]['tiles'][1]['title'] == 'CRACKING'
    assert re.match(
        '[0-9.]+M',
        status[0]['tiles'][2]['title'],
    )
    assert status[0]['tiles'][3]['title'] > 0
    assert re.match(
        '[0-9.]+%',
        status[0]['tiles'][4]['title'],
    )
    assert re.match(
        '[0-9.]+ s',
        status[0]['tiles'][5]['title'],
    )
    assert re.match(
        '[0-9.]+ s',
        status[0]['tiles'][6]['title'],
    )

    rv = client.get('/').data.decode()
    assert 'Running' in rv
    assert 'Successful guesses' in rv
    assert 'CRACKING' in rv
    assert re.search(
        r'[0-9.]+[KMG]?</p>\s*<p class="subtitle">Hashes/Second',
        rv,
        re.MULTILINE,
    ) is not None
    assert re.search(
        r'[0-9]+</p>\s*<p class="subtitle">Successful guesses',
        rv,
        re.MULTILINE,
    ) is not None
    assert re.search(
        r'[0-9]{1,3}%</p>\s*<p class="subtitle">Progress',
        rv,
        re.MULTILINE,
    ) is not None
    assert job.audit.state.name == "CRACKING"

    flask.backend._job.wait_until_finished()
    assert flask.backend._job is None
    assert job.cracker._process.returncode == 0
    assert "Audit with ID %s has a new state: FINISHED" % uuid \
        in caplog.records[-1].message

    # Check report
    with models.session_scope() as s:
        audit = s.query(models.Audit).filter(models.Audit.uuid == uuid).one()
        report = audit.report
        assert report is not None
        assert abs(report.cracked - 0.195) < 0.01
        assert abs(report.mean_pw_len - 6.75) < 0.01
        assert report.largest_clique == 17
        assert abs(report.cliquiness - 0.308) < 0.01

    rv = client.get('/report?id=' + uuid).data.decode()
    assert 'Total hash count' in rv
    assert 'Mean password length' in rv
    assert '>6.75<' in rv
    assert 'dumbos' in rv

    # Check mails
    print(mock_server.received_messages)
    assert(mock_server.received_messages_count() == 2)
    assert(mock_server.received_message_matching(
        ".*Bcc: monkey@contoso.local.*"
    ))
    assert(mock_server.received_message_matching(r".*domain\.local\\chris.*"))
    assert(mock_server.received_message_matching(".*dumbos.*"))
    assert(mock_server.received_message_matching(
        ".*Bcc: admin1@contoso.local.*"
    ))
    assert(mock_server.received_message_matching(".*were recovered.*"))
    assert(mock_server.received_message_matching(".*Start:.*"))
    assert(mock_server.received_message_matching(
        '.*Your password has been cracked.*'
    ))
    mock_server.reset()

    rv = client.get('/').data.decode()
    assert 'Ready' in rv

    # Check past audit info meant for homepage
    status = flask.backend.get_status()
    assert re.match(
        '[0-9.]+ s',
        status[1]['tiles'][0]['title'],
    )
    assert re.match(
        '[0-9.]+ s',
        status[1]['tiles'][1]['title'],
    )
    assert status[1]['tiles'][2]['title'] == 1726
    assert status[1]['tiles'][3]['title'] > 0
    assert status[1]['tiles'][4]['title'] > 0

    rv = client.get('/audits').data.decode()
    assert 'FINISHED' in rv
