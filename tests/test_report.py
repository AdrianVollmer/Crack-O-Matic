import sys
import os

import pytest


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_PATH, '..'))


NTDS = os.path.join(SCRIPT_PATH, 'data', 'ntds.txt')
CRACKED = os.path.join(SCRIPT_PATH, 'data', 'cracked.txt')


@pytest.fixture
def cracked(request):
    hashes = []
    passwords = []
    with open(CRACKED, 'r') as f:
        lines = f.readlines()
    for line in lines:
        p = line.split(':')[1]
        passwords.append(p)
    with open(NTDS, 'r') as f:
        lines = f.readlines()
    for line in lines:
        h = line.split(':')[3]
        hashes.append(h)
    yield hashes, passwords


def test_text_report(cracked):
    hashes, passwords = cracked
    from crackomatic.reports import create_report, create_text_report
    r = create_report(passwords, hashes)
    text = create_text_report(r)
    assert '1726' in text
    assert '82.62%' in text
    assert '8.70' in text
    assert '30.84%' in text
    assert '["angel", 6]' in r.top_basewords
    assert '["?", 1426]' in r.top_patterns
    print(r.__dict__)

    r = create_report(['foo'], ['bar'])
    assert r.cliquiness is None
