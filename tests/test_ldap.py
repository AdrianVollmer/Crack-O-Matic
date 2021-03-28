import os
import sys


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_PATH, '..'))

from common import get_ca_file  # noqa


def test_ldap_query(global_data):
    from crackomatic.ldap import ldap_query

    domain_dn = 'DC=' + ',DC='.join(global_data['DOMAIN'].split('.'))
    binddn = '%(DOMAINUSER)s@%(DOMAIN)s' % global_data
    password = global_data['DOMAINPASS']
    url1 = "ldaps://%s:636" % global_data['HOST']
    #  url2 = "ldap://%s:396" % global_data['HOST']
    search_filter = '(objectClass=user)'
    search_attribute = ['sAMAccountName']

    ca_file = get_ca_file(url1)
    result = ldap_query(url1, domain_dn, ca_file, binddn, password,
                        search_filter, search_attribute)

    assert result
    admin = result['CN=%s,CN=Users,%s' % (global_data['DOMAINUSER'],
                                          domain_dn)]
    assert admin['sAMAccountName'][0] == global_data['DOMAINUSER'].encode()


def test_ldap_auth(global_data):
    from crackomatic.user import User
    url = 'ldaps://%s:636' % global_data['HOST']
    dn = "DC=" + ",DC=".join(global_data['DOMAIN'].split('.'))

    config = {
        'ldap_url': url,
        'ca_file': get_ca_file(url),
        'basedn': 'CN=Users,%s' % dn,
        'binddn': 'CN=%%s,CN=Users,%s' % dn,
        'filter': "(sAMAccountName=%s)" % global_data['DOMAINUSER'],
    }

    auth = User.authenticate_ldap(
        global_data['DOMAINUSER'],
        global_data['DOMAINPASS'],
        config,
    )

    assert auth

    # Invalid password
    auth = User.authenticate_ldap(
        global_data['DOMAINUSER'],
        'invalid password',
        config,
    )

    assert not auth

    config['filter'] = (
        "(&(objectClass=user)"
        "(memberOf=CN=NonExistentGroup,CN=Users,%s))" % dn
    )
    # Insufficient permissions
    auth = User.authenticate_ldap(
        global_data['DOMAINUSER'],
        global_data['DOMAINPASS'],
        config,
    )

    assert not auth
