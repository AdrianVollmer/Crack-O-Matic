import time
import os
from datetime import datetime as dt, timedelta

import pytest


@pytest.fixture
def cracker(request):
    return request.param


@pytest.fixture(scope="function")
def crack(cracker, global_data):
    # Should take minutes
    from crackomatic.cracker import John, Hashcat

    if cracker == 'Hashcat':
        crack = Hashcat(
                global_data['NTDS'],
                global_data['WORDLIST'],
                '/usr/share/hashcat/rules/best64.rule',
                global_data['HASHCAT_PATH'],
        )
    elif cracker == 'John':
        crack = John(
                global_data['NTDS'],
                global_data['WORDLIST'],
                'best64',
                global_data['JOHN_PATH'],
        )
    yield crack


@pytest.fixture(scope="function")
def crack_short(cracker, global_data):
    # Should take seconds
    from crackomatic.cracker import John, Hashcat

    if cracker == 'Hashcat':
        crack = Hashcat(
                global_data['NTDS'],
                global_data['WORDLIST'],
                '/usr/share/hashcat/rules/best64.rule',
                global_data['HASHCAT_PATH'],
        )
    elif cracker == 'John':
        crack = John(
                global_data['NTDS'],
                global_data['WORDLIST'],
                'best64',
                global_data['JOHN_PATH'],
        )
    yield crack


@pytest.fixture(scope="function")
def crack_long(cracker, global_data):
    # Should take hours to days
    from crackomatic.cracker import John, Hashcat

    if cracker == 'Hashcat':
        crack = Hashcat(
                global_data['NTDS'],
                global_data['WORDLIST'],
                '/usr/share/hashcat/rules/dive.rule',
                global_data['HASHCAT_PATH'],
                args=['--force'],
        )
    elif cracker == 'John':
        crack = John(
                global_data['NTDS'],
                global_data['WORDLIST'],
                'korelogic',
                global_data['JOHN_PATH'],
        )
    yield crack


@pytest.mark.parametrize('cracker', ['John', 'Hashcat'], indirect=True)
def test_cracker(crack_short):
    from crackomatic.cracker import John
    crack = crack_short
    crack.wait_until_finished()

    if isinstance(crack, John):
        assert crack._process.returncode == 0
        assert crack.output['stdout'].startswith('Loaded 1194 password hashes')
        assert crack.output['stderr'].startswith(
            'Using default input encoding: UTF-8'
        )
        assert 'Session completed' in crack.output['stderr']
    else:
        assert crack.output['stdout'].startswith('hashcat (v')
        assert crack.output['stderr'] == ''

    assert len(crack.passwords) == 336
    assert 'domain.local\\1234' in crack.passwords
    assert crack.passwords['domain.local\\1234'] == 'margarita'
    assert 'margarita' not in crack.output['stdout']
    assert 'margarita' not in crack.output['stderr']

    assert not os.path.exists(crack._potfile)


@pytest.mark.parametrize('cracker', ['Hashcat', 'John'], indirect=True)
def test_cracker_status(crack_long):
    crack = crack_long
    status = []
    time.sleep(20)
    for i in range(5):
        time.sleep(10)
        status.append(crack.get_status())
        if crack._process.returncode is not None:
            break

    print(status)
    # Program should still be running
    assert crack._process.returncode is None
    if crack._process.returncode is None:
        assert os.path.exists(crack._potfile)

    crack.abort()
    crack.wait_until_finished()

    assert len(status) > 2
    for i, s in enumerate(status[:-1]):
        assert s['progress'] <= status[i+1]['progress']
        assert s['progress'] >= 0
        assert s['progress'] <= 100
        assert s['guesses'] <= status[i+1]['guesses']
        assert s['guesses'] >= 0
        assert s['speed'] > 1000
        assert s['ETA'] < dt.now() + timedelta(days=2000)
        assert s['ETA'] > dt.now() - timedelta(seconds=5)

    assert not os.path.exists(crack._potfile)
