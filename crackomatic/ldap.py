import ldap


def ldap_query(url, basedn, ca_file, binddn, password, search_filter,
               search_attributes=[]):
    '''Perform an LDAP query and return a list of its results

    url: URL of the LDAP server, e.g. ldaps://DC01.contoso.local:396
    basedn: The base DN, e.g. DC=contoso,DC=local
    ca_file: Path to a file containing the certificate of a CA (PEM)
    binddn: The bind DN, e.g. username@contoso.local
    password: The corresponding password
    search_filter: An LDAP search filter, e.g. (objectClass=user)
    search_attributes: List of attributes which to return, e.g.
        ['sAMAccountName', 'adminCount']
    '''
    conn = ldap.initialize(url)
    search_scope = ldap.SCOPE_SUBTREE
    conn.protocol_version = ldap.VERSION3
    if url.startswith('ldaps'):
        conn.set_option(ldap.OPT_X_TLS_CACERTFILE, ca_file)
        conn.set_option(ldap.OPT_X_TLS, ldap.OPT_X_TLS_DEMAND)
        conn.set_option(ldap.OPT_X_TLS_DEMAND, True)
        conn.set_option(ldap.OPT_X_TLS_NEWCTX, 0)
    conn.simple_bind_s(binddn, password)
    result_set = conn.search_s(
        basedn,
        search_scope,
        search_filter,
        search_attributes,
    )
    conn.unbind_s()
    return dict(result_set)
