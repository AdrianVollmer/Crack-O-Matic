import time
from crackomatic.constants import AuditState, AuditFrequency


# Valid audit config
def audit_config(global_data):
    ldap_url = 'ldaps://%s:%d' % (global_data['HOST'], 636)
    ca_file = get_ca_file(ldap_url)
    return dict(
        user=global_data['DOMAINUSER'],
        domain=global_data['DOMAIN'],
        dc_ip=global_data['HOST'],
        password=global_data['DOMAINPASS'],
        email_field='email',
        ldap_url=ldap_url,
        ca_file=ca_file,
        user_filter='(objectClass=person)',
        admin_filter='(&(objectClass=user)(memberOf=cn=crackomaticAdmins))',
        subject='Subject',
        message='Your password has been cracked',
        include_cracked='y',
        start='',
        frequency=int(AuditFrequency.JUST_ONCE),
    )


def cracker_config(global_data):
    return dict(
        cracker='John',
        binary_path=global_data['JOHN_PATH'],
        wordlist_path=global_data['WORDLIST'],
        rule_path='best64',
        section='cracker',
    )


email_config = dict(
    smtphost='localhost',
    smtpport=25025,
    # must be 'empty' for 'no'
    smtptls='',
    smtp_cafile='',
    smtpuser='',
    smtppass='',
    smtpsender="noreply@crackomatic.com",
    section='email',
)

auth_config = dict(
    test='one',
    section='authentication',
)


def get_ca_file(url):
    '''Retrieve and save TLS cert to file; return filename'''
    import ssl
    import tempfile

    tempf = tempfile.NamedTemporaryFile(mode='w+', delete=False)
    protocol, rest = url.split('://')
    hostname, port = rest.split(':')
    cert = ssl.get_server_certificate((hostname, port))
    tempf.write(cert)
    return tempf.name


def mock_run(self):
    """Just wait 10 seconds instead of doing anything in a Job"""
    self.lock.acquire()
    self.update_state(AuditState.REPLICATING)
    time.sleep(10)
    self.update_state(AuditState.FINISHED)
    self.lock.release()
    self.cb_cleanup(self.audit.uuid)


def mock_get_hashes(domain, username, password, root_dir='/tmp',
                    ip=None, history=False):
    time.sleep(10)
    with open('tests/data/ntds.txt', 'r') as f:
        result = f.read()
    return result


def mock_ldap_query(url, basedn, ca_file, binddn, password, search_filter,
                    search_attributes=[]):
    if 'user' in search_filter:
        accounts = ['monkey', 'billy', 'freedom']
    else:
        accounts = ['admin1', 'admin2', 'admin3']
    return {
        account: {
            'sAMAccountName': [account.encode()],
            'email': [account.encode()+b'@contoso.local']
        } for account in accounts
    }
