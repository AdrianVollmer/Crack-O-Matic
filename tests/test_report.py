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
    from crackomatic.reports import create_report, create_text_report, \
        create_figures

    # Test an expected report
    r = create_report(passwords, hashes)
    print(r.__dict__)
    text = create_text_report(r)
    figures = create_figures(r)
    assert '1726' in text
    assert '82.62%' in text
    assert '8.70' in text
    assert '30.84%' in text
    assert '["angel", 6]' in r.top_basewords
    assert 'angel: 6' in text
    assert '["?", 1426]' in r.top_patterns
    assert '?: 1426' in text
    assert '<svg' in figures[0]['html']
    assert '82.6%' in figures[0]['html']
    assert 'Percentage of hashes cracked' in figures[0]['title']
    assert '<p class="scalar">1726</p>' == figures[1]['html']

    # Test a somewhat irregular report
    r = create_report(['foo'], ['bar'])
    print(r.__dict__)
    text = create_text_report(r)
    figures = create_figures(r)
    assert r.cliquiness is None
    assert '100.00%' in text
    assert '100%' in figures[0]['html']
    assert '1' in figures[1]['html']
    assert '3.0' in figures[5]['html']

    # Test if no hashes have been cracked
    r = create_report([], ['foo']*10)
    print(r.__dict__)
    text = create_text_report(r)
    figures = create_figures(r)
    print(text)
    assert 'Mean password length' not in text
    assert 'Length distribution' not in text
    assert 'Top patterns' not in text
    assert figures[6]['html'] == ''
    assert figures[7]['html'] == ''
    assert figures[8]['html'] == ''
    assert figures[9]['html'] == ''

    # Test if no passwords have been supplied
    r = create_report([], [])
    print(r.__dict__)
    text = create_text_report(r)
    figures = create_figures(r)
    assert 'Mean password length' not in text
    assert 'Length distribution' not in text
    assert 'Top patterns' not in text
    assert figures[1]['html'] == '<p class="scalar">0</p>'
    assert figures[3]['html'] == ''
    assert figures[5]['html'] == ''
    assert figures[6]['html'] == ''
    assert figures[7]['html'] == ''
    assert figures[8]['html'] == ''
    assert figures[9]['html'] == ''
