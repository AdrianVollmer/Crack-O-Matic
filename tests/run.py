#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import argparse
import tempfile
import json
from datetime import datetime as dt

from dotenv import load_dotenv

from pathlib import Path
path = os.path.dirname(os.path.realpath(__file__))
sys.path.append(str(Path(path).absolute().parent))


from common import mock_run, mock_get_hashes  # noqa

parser = argparse.ArgumentParser(
    description="Test application for crackomatic"
)

parser.add_argument(
    '--replace-job', action='store_true', default=False,
    help="replace replication as well as cracking; just return passwords",
)

parser.add_argument(
    '--replace-replication', action='store_true', default=False,
    help="return static data instead of performing replication",
)

parser.add_argument(
    '--disable-auth', action='store_true', default=False,
    help="disable authentication",
)

parser.add_argument(
    '--database', choices=['fresh', 'filled', 'const'],
    default='const',
    help="choose which database to use",
)


class AttrDict(dict):
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

    def __getattr__(self, attr):
        return self.get(attr)

    def __getstate__(self):
        return self

    def __setstate__(self, state):
        self.update(state)
        self.__dict__ = self


def fill_database(crackomatic):
    from crackomatic.constants import AuditState, AuditFrequency
    from crackomatic.models import session_scope, Audit, Report
    from common import get_ca_file, email_config

    host = os.environ.get('HOST')
    domain = os.environ.get('DOMAIN')
    ldap_url = 'ldaps://%s:636' % host
    ca_file = get_ca_file(ldap_url)

    # Sample config
    config = {
        'cracker': dict(
            cracker='John',
            binary_path=os.environ.get('JOHN_PATH'),
            wordlist_path='tests/data/openwall.net-all.txt',
            rule_path='best64',
            section='cracker',
        ),
        'email': email_config,
        'authentication': dict(
            ldap_url='',
            ca_file='',
            binddn='',
            filter='',
        ),
    }

    # Sample audit
    audit = AttrDict(
        uuid='c0ffee-4abc-0934230492059-2348',
        user='Administrator',
        domain=domain,
        password='Summer2020',
        email_field='mail',
        ldap_url=ldap_url,
        ca_file=ca_file,
        user_filter="(objectClass=user)",
        admin_filter="(AdminCount=1)",
        subject="About your password...",
        message="""Dear user, ...
    foo

    bar

    baz
    """,
        include_cracked=True,
        start=dt.strptime("2022-10-28 18:12:43", "%Y-%m-%d %H:%M:%S"),
        end=dt.strptime("2022-10-28 18:18:23", "%Y-%m-%d %H:%M:%S"),
        state=AuditState(1),
        frequency=AuditFrequency(3),
    )

    # Sample Report
    report = AttrDict(
        cracked=.38,
        total_hashes=394,
        mean_pw_len=12.88,
        lengths=json.dumps({12: 5, 13: 7, 11: 4, 8: 3, 17: 1}),
        cliques=json.dumps({1: 99, 2: 23, 3: 17, 4: 3, 5: 1, 8: 1}),
        largest_clique=8,
        cliquiness=.65,
        char_classes=json.dumps({1: 4, 2: 7, 3: 5, 4: 10}),
        top_basewords=json.dumps([
            ['Password', 17],
            ['Secret', 14],
            ['Winter', 11],
            ['Summer', 7],
            ['Start', 6],
            ['asdfghjkl', 4],
            ['Banana', 2],
        ]),
        top_patterns=json.dumps([
            ["Abc1", 21],
            ["Abc12", 18],
            ["Abc123", 17],
            ["Abc1234", 9],
            ["Abcdef!", 8],
            ["abcdef", 6],
            ["123456", 3],
        ]),
    )
    with session_scope() as s:
        audit = Audit(
            **dict(audit),
            report=Report(**dict(report)),
        )
        s.add(audit)
    from crackomatic.flask import backend
    for k, v in config.items():
        backend.config.update(k, v)


def print_msg(data):
    print("E-Mail received:")
    print(data)


class User(object):
    def get_id(self):
        return "TestAdmin"

    def is_authenticated(self):
        return True


def run(args, crackomatic_args):
    # Run SMTP server
    from smtpmock import MockSMTPServer
    smtpserver = MockSMTPServer(
        hostname='localhost',
        port=25025,
        callback=print_msg,
    )

    # Patch authentication
    import flask_login
    if args.disable_auth:
        flask_login.login_required = lambda f: f
        flask_login.current_user = User()

    import crackomatic
    import crackomatic._version

    # Replace version
    crackomatic._version.__version__ = 'TEST'

    # Patch backend
    if args.replace_job:
        setattr(crackomatic.job, 'run', mock_run)
    if args.replace_replication:
        setattr(crackomatic.job,
                "get_hashes", mock_get_hashes)

    # Load app
    from crackomatic.__main__ import init, run_web
    crackomatic_args = init(crackomatic_args)

    # Fill DB
    if args.database == 'filled':
        fill_database(crackomatic)

    # Run
    run_web(crackomatic_args)
    smtpserver.stop()


def main():
    load_dotenv(dotenv_path='./tests/.env', verbose=True)
    assert os.environ.get('HOST'), "You must have an .env file in ./tests/"
    args = parser.parse_args()

    # Pass these arguments to crackomatic
    crackomatic_args = [
        '--debug',
        'web',
    ]
    if args.database != 'const':
        tmpfile = tempfile.NamedTemporaryFile(delete=False)
        crackomatic_args = [
            '--db-path', tmpfile.name,
        ] + crackomatic_args

    run(args, crackomatic_args)


if __name__ == "__main__":
    main()
