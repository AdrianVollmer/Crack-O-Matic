import shutil
import os
import subprocess
from logging import getLogger
log = getLogger(__name__)

_DIR_NAME = 'smb_dc'


def patched_do_join(ctx):
    from samba.dcerpc import misc
    log.debug("Run patched do_join")
    ctx.nc_list = [ctx.config_dn, ctx.schema_dn]
    ctx.full_nc_list = [ctx.base_dn, ctx.config_dn, ctx.schema_dn]

    ctx.ntds_guid = misc.GUID(ctx.samdb.schema_format_value(
        'objectGUID',
        b'\x83\xb7\xd6\xc1b]\xb5B\x8e\xdbkvw2dz',
    ))  # any GUID will do
    ctx.rid_manager_dn = None
    ctx.join_provision()
    ctx.join_replicate()


def remove_dir(path):
    shutil.rmtree(path, ignore_errors=True)


def replicate(root_dir, domain, ip, username, password, history=False):
    '''Wrapper for samba-tool'''
    try:
        from samba import join
        from samba.netcmd.main import cmd_sambatool
    except ImportError:
        raise RuntimeError("Samba not installed")
    try:
        # Monkey patch the samba libs
        join.DCJoinContext.do_join = patched_do_join
    except AttributeError:
        raise RuntimeError("Samba not compatible")

    cmd = cmd_sambatool()
    log.info("Start replication")
    # change all directories so we don't need root
    options = {
        "smb passwd file": "%(ROOT)s/smbpasswd",
        "log file": "%(ROOT)s/samba.log",
        "lock directory": "%(ROOT)s/samba",
        "state directory": "%(ROOT)s/samba",
        "cache directory": "%(ROOT)s/samba",
        "pid directory": "%(ROOT)s/samba",
        "private dir": "%(ROOT)s/samba",
        "ncalrpc dir": "%(ROOT)s/samba",
        "netbios name": "CRACKREP",  # TODO check if name exists
    }
    opts = ['--option=%s=%s' % (k, v % {"ROOT": root_dir})
            for k, v in options.items()]
    retval = cmd._run(
        "samba-tool",
        "domain",
        "join",
        str(domain),
        "DC",
        "--username=%s" % username,
        "--password=%s" % password,
        "--ipaddress=%s" % ip,
        "--server=%s" % ip,
        "--realm=%s" % domain,
        *opts
    )
    if retval and retval != 0:
        raise RuntimeError(
            "Replication failed with return code %d" % retval
        )


def read_hashes_from_sam(root_dir):
    '''Call pdbedit to retrieve hashes from SAM database'''
    log.debug("Read hashes from file in %s/samba" % root_dir)
    cmd = [
        'pdbedit',
        '-L',
        '-w',
        '--option=private dir=%s/samba' % root_dir
    ]
    p = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    result, errors = p.communicate()
    if p.returncode:
        log.error(errors.decode())
        raise RuntimeError("pdbedit exited with return code %d" % p.returncode)
    result = result.splitlines()
    result = [x.decode().split(':') for x in result]
    result = [[x[0], x[1], x[2].lower(), x[3].lower()] for x in result]
    result = [
        "%s:%s:%s:%s:::" % tuple(x[:4])
        for x in result
    ]
    result = '\n'.join(result)
    return result


def get_hashes(domain, username, password, root_dir='/tmp',
               ip=None, history=False):

    root_dir = os.path.join(root_dir, _DIR_NAME)
    remove_dir(root_dir)
    os.mkdir(root_dir)
    try:
        if not ip:
            ip = domain
        replicate(root_dir, domain, ip, username, password)
        hashes = read_hashes_from_sam(root_dir)
        return hashes
    finally:
        remove_dir(root_dir)
