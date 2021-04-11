from logging import getLogger
from threading import Thread
from tempfile import TemporaryDirectory
import os
from datetime import datetime as dt

from .smb import get_hashes
from .cracker import get_cracker
from .reports import create_text_report, create_report
from .email import send_mails
from .constants import AuditState, FINISHED_STATES
from .ldap import ldap_query

log = getLogger(__name__)


ADMIN_MSG = """
This is the report of the latest Crack-O-Matic audit.

%(URL)s

Start: %(START)s
End: %(END)s

%(REPORT)s

%(CRACKED_LIST)s"""


class Job(Thread):
    def __init__(self, audit, lock, cracker_config, email_config,
                 cb_update=None, cb_cleanup=None, password=None):
        self.audit = audit
        log.debug("Starting job for audit %s" % self.audit.uuid)
        self.lock = lock
        self.cracker_config = cracker_config
        self.email_config = email_config
        self.cb_update = cb_update  # cb = callback
        self.cb_cleanup = cb_cleanup
        self.password = password
        self.cracker = None

        self.report = None
        self.text_report = "Report not yet generated"
        self._root_dir = TemporaryDirectory(
            prefix='crackomatic_job',
            suffix=self.audit.uuid,
        )
        super().__init__()

    def update_state(self, state):
        self.audit.state = state
        log.info("Audit with ID %s has a new state: %s"
                 % (self.audit.uuid, self.audit.state.name))
        if state == AuditState.REPLICATING:
            self.audit.start = dt.now()
        elif state in FINISHED_STATES:
            self.audit.end = dt.now()
        if self.cb_update:
            self.cb_update(self.audit)

    def wait_until_finished(self):
        self.lock.acquire()
        self.lock.release()

    def run(self):
        try:
            self.lock.acquire()
            self.update_state(AuditState.REPLICATING)
            hashes = get_hashes(
                self.audit.domain,
                self.audit.user,
                self.password or self.audit.password,
                ip=self.audit.dc_ip,
                root_dir=self._root_dir.name,
            )
            self.update_state(AuditState.CRACKING)
            hash_file = os.path.join(self._root_dir.name, 'hashfile')
            with open(hash_file, 'w') as f:
                f.write(hashes)
            self.cracker = get_cracker(
                self.cracker_config['cracker'],
                hash_file,
                self.cracker_config['wordlist_path'],
                self.cracker_config['rule_path'],
                self.cracker_config['binary_path'],
                root_dir=self._root_dir.name,
            )
            self.cracker.wait_until_finished()
            if self.cracker.passwords is None:
                raise RuntimeError(
                    "Something went wrong while cracking; check the logs"
                )
            self.update_state(AuditState.ANALYZING)
            passwords = [p for p in self.cracker.passwords.values()
                         if p is not None]
            hashes = [h.split(':')[3] for h in hashes.splitlines()]
            self.analyze(passwords, hashes)
            users = list(self.cracker.passwords.keys())
            self.update_state(AuditState.SENDING_EMAILS)
            self.send_notifications(users)
            self.update_state(AuditState.FINISHED)
        except Exception as e:
            self.update_state(AuditState.FAILED)
            log.exception(e)
            raise e
        finally:
            try:
                if self.cb_cleanup:
                    self.cb_cleanup(self.audit.uuid)
            finally:
                self.lock.release()
                self._root_dir.cleanup()

    def get_email_addresses(self, filter, audit):
        dn = 'DC=' + ',DC='.join(audit.domain.split('.'))
        bind = "%s@%s" % (audit.user, audit.domain)
        emails = ldap_query(
            audit.ldap_url,
            dn,
            audit.ca_file,
            bind,
            self.password,
            filter,
            ['sAMAccountName', audit.email_field],
        )
        emails = {
            v['sAMAccountName'][0].decode().upper():
                v[audit.email_field][0].decode()
            for v in emails.values()
            if audit.email_field in v
        }
        return emails

    def send_notifications(self, compromised_users):
        from .constants import URL
        audit = self.audit
        user_emails = self.get_email_addresses(audit.user_filter, audit)
        admin_emails = self.get_email_addresses(audit.admin_filter, audit)
        # Only inform compromised users
        user_emails = [
            user_emails.get(u.split('\\')[1].upper()) if '\\' in u else
            user_emails.get(u.upper()) for u in compromised_users
        ]
        # Remove invalid entries
        user_emails = [address for address in user_emails
                       if address and '@' in address]
        if user_emails:
            send_mails(
                user_emails,
                audit.subject,
                audit.message,
                self.email_config,
            )

        # Send report to admins
        if audit.include_cracked:
            cracked_list = (
                "\n\nThe following users' passwords were recovered:\n\n"
            ) + '\n'.join(sorted(compromised_users))
        else:
            cracked_list = ""
        print("URL: ", URL)
        url = ("%s/report?id=%s" % (URL, audit.uuid)) if URL else ''
        admin_msg = ADMIN_MSG % {
            "START": audit.start,
            "END": str(dt.now()),
            "REPORT": self.text_report,
            "CRACKED_LIST": cracked_list,
            "URL": url,
        }
        admin_emails = list(admin_emails.values())

        if admin_emails:
            send_mails(
                admin_emails,
                "Crack-O-Matic: Report",
                admin_msg,
                self.email_config,
            )
        else:
            log.error("No admin e-mail addresses found")

    def analyze(self, passwords, hashes):
        # This step is not critical, so we wrap it in a try-block
        try:
            self.report = create_report(passwords, hashes)
            self.text_report = create_text_report(self.report)
        except Exception as e:
            log.error("An error occurred while creating the report for audit with ID %s"  # noqa
                      % self.audit.uuid)
            log.exception(e)
