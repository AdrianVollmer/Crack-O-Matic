import difflib
import os
import sys
import io

import ldap
import ldif


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(SCRIPT_PATH, '..'))


def ldap_dump(global_data):
    conn = ldap.initialize('ldaps://%s' % global_data["HOST"])
    conn.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_NEVER)
    conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
    basedn = "dc=" + ",dc=".join(global_data["DOMAIN"].split('.'))
    pw = global_data["DOMAINPASS"]
    user_dn = "%s@%s" % (global_data["DOMAINUSER"], global_data["DOMAIN"])
    searchFilter = "(objectclass=*)"
    searchAttribute = []
    searchScope = ldap.SCOPE_SUBTREE
    conn.protocol_version = ldap.VERSION3
    conn.simple_bind_s(user_dn, pw)
    ldap_result_id = conn.search(basedn, searchScope,
                                 searchFilter, searchAttribute)
    result_set = []
    while 1:
        result_type, result_data = conn.result(ldap_result_id, 0)
        if (result_data == []):
            break
        else:
            if result_type == ldap.RES_SEARCH_ENTRY:
                result_set.append(result_data)
    conn.unbind_s()
    f = io.StringIO("some initial text data")
    ldif_writer = ldif.LDIFWriter(f)
    for r in result_set:
        ldif_writer.unparse(r[0][0], r[0][1])
    return f.getvalue()


def test_dc_rep(global_data):
    from crackomatic.log import init_log
    init_log(level='DEBUG', sql=False)
    from crackomatic.smb import get_hashes, _DIR_NAME
    ROOT_DIR = '/tmp'

    dump_before = ldap_dump(global_data)
    assert "CRACKREP" not in dump_before
    assert global_data['DOMAIN'] in dump_before

    hashes = get_hashes(
        global_data['DOMAIN'],
        global_data['DOMAINUSER'],
        global_data['DOMAINPASS'],
        ip=global_data['HOST'],
    )
    dump_after = ldap_dump(global_data)

    assert "CRACKREP" not in dump_after
    diff = difflib.unified_diff(dump_before.splitlines(),
                                dump_after.splitlines())
    assert '\n'.join(diff) == ""
    assert 'krbtgt:' in hashes
    assert 'Administrator:' in hashes
    assert ':7cbdc9e02a9d42705dd88396fea70f32:' in hashes
    # Check if dir is deleted
    assert not os.path.isdir(os.path.join(ROOT_DIR, _DIR_NAME))
