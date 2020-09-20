import os
import sys
#  import requests

import pytest
from dotenv import load_dotenv


WL_URL = 'https://raw.githubusercontent.com/danielmiessler/SecLists/9f4d672e98a837fb1f3d59095df36b63af6987d1/Passwords/openwall.net-all.txt'  # noqa
WL_SHA256 = '0d54baabd3fd7d8cbad6e7181c3a7d3482f5b1cb8139b8dc39ffc0bee0e8f725'  # noqa

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_PATH + '/../')
DATA_DIR = os.path.join(SCRIPT_PATH, 'data')

DB_FILE = '/tmp/crackomatic.db'
DB = 'sqlite:///' + DB_FILE
try:
    os.remove(DB_FILE)
except OSError:
    pass


def get_sha256_sum(filename):
    import hashlib
    BUF_SIZE = 65536
    sha2 = hashlib.sha256()

    with open(filename, 'rb') as f:
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            sha2.update(data)
    return sha2.hexdigest()


@pytest.fixture
def global_data():
    load_dotenv()
    result = dict(
        DB=DB,
        DATA_DIR=os.path.join(SCRIPT_PATH, 'data'),
        NTDS=os.path.join(DATA_DIR, 'ntds.txt'),
        WORDLIST=os.path.join(DATA_DIR, 'openwall.net-all.txt'),
        HASHCAT_PATH=os.environ.get("HASHCAT_PATH", "/usr/bin/hashcat"),
        JOHN_PATH=os.environ.get("JOHN_PATH", "/usr/bin/john"),
        DOMAIN=os.environ.get("DOMAIN"),
        DOMAINPASS=os.environ.get("DOMAINPASS"),
        DOMAINUSER=os.environ.get("DOMAINUSER", "Administrator"),
        HOST=os.environ.get("HOST"),
    )

    assert result["DOMAIN"], "You must specify a test domain"
    assert result["DOMAINUSER"], "You must specify a test domain user"
    assert result["DOMAINPASS"], "You must specify a password"
    assert result["HOST"], ("You must specify a hostname of a DC"
                            "in the test domain")
    assert os.path.exists(result['WORDLIST']), (
        "You must download %s and place it at %s" % (
            WL_URL, result['WORDLIST']
        ))
    assert WL_SHA256 == get_sha256_sum(result['WORDLIST']), (
        "The SHA-256 of %s does not match" % result['WORDLIST']
    )

    return result


@pytest.fixture(scope='session')
def mock_server():
    import smtpmock
    server = smtpmock.MockSMTPServer("localhost", 25025)
    yield server
    server.stop()
