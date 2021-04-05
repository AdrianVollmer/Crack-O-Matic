import argparse
from logging import getLogger
import os
import sys

from xdg.BaseDirectory import save_data_path
import toml

from ._version import __version__

DATA_DIR = save_data_path('crackomatic')
DB_PATH = os.path.join(DATA_DIR, 'crackomatic.db')


logger = getLogger(__name__)


parser = argparse.ArgumentParser(
    description="Find and notify users in your Active Directory "
                "with weak passwords",
)

parser.add_argument(
    '-v', '--version', action='version', version='Crack-O-Matic ' + __version__
)

parser.add_argument(
    '-d', '--debug', action='store_true', default=False,
    help="log debugging information (default: %(default)s)",
)

parser.add_argument(
    '-b', '--db-path', default=DB_PATH,
    help="path to the database location (default: %(default)s)",
)

parser.add_argument(
    '-C', '--config-path', default='/etc/crackomatic/crackomatic.conf',
    help="path to the config file location (default: %(default)s)",
)


# Add subparsers
# ==============


subparsers = parser.add_subparsers(dest='operation', required=True)


# Add web subparsers
# ==================


parser_web = subparsers.add_parser(
    'web',
    help="Run the Flask-based web front-end",
)

parser_web.add_argument(
    '-p', '--port', default=3000, type=int,
    help="listening port (default: %(default)s)",
)

parser_web.add_argument(
    '-a', '--local-address', default='localhost',
    help="listening address (default: %(default)s)",
)

parser_web.add_argument(
    '-k', '--key',
    help="Path to a private key file in PEM format",
)

parser_web.add_argument(
    '-c', '--cert',
    help="Path to an X.509 certificate file in PEM format",
)


# Add audit subparser
# ===================


parser_audit = subparsers.add_parser(
    'audit',
    help="Perform an audit immediately",
)

parser_audit.add_argument(
    '-i', '--interactive', default=False, action='store_true',
    help="Prompt for missing fields (useful for passwords)",
)

audit_group = parser_audit.add_mutually_exclusive_group()

audit_group.add_argument(
    'audit_file', default=None, nargs='?',
    help="Path to a file containing all the necessary information"
    " to perform the audit",
)

audit_group.add_argument(
    '-s', '--sample', default=False, action='store_true',
    help="Output a sample audit config file to stdout and exit;"
         " read the docs to learn how to fill out this file",
)

audit_group.add_argument(
    '-d', '--description', default=False, action='store_true',
    help="Print a description of all required fields and exit;",
)

# Add user subparser
# ==================


parser_user = subparsers.add_parser(
    'user',
    help="Manage local users",
)

parser_user.add_argument(
    'action',
    choices=['list', 'add', 'delete', 'change'],
    default='list',
    help="Perform this action",
)

parser_user.add_argument(
    'username', default='', type=str, nargs='?',
    help="User name to perform the action on",
)


def parse_args(argv=None):
    args = parser.parse_args(argv)
    if not argv:
        argv = sys.argv

    # Load TOML config file
    if os.path.exists(args.config_path):
        with open(args.config_path, 'r') as f:
            config = toml.load(f)
    else:
        config = {}

    # Set arguments that haven't been set via command line
    for p in ['port', 'local_address', 'key', 'cert']:
        argument = '--' + p.replace('_', '-')
        if p in config and (argv is None or argument not in argv):
            setattr(args, p, config[p])

    return args
