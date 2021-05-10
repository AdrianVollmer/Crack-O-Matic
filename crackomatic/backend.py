from logging import getLogger
from threading import Lock, Thread
from datetime import datetime as dt, timedelta
from uuid import uuid4
from time import sleep
import json

from sqlalchemy import func
from babel.dates import format_timedelta

from ._version import __version__
from .job import Job
from .models import Meta, session_scope, Audit, Log, freeze, Config
from .config import CrackomaticConfig
from .constants import AuditState, AuditFrequency, FINISHED_STATES

log = getLogger(__name__)


class Backend(object):
    _SINGLETON = False

    def __init__(self, with_cronjob=True):
        assert not self._SINGLETON, "Backend already instantiated"
        self._SINGLETON = True
        log.info("Starting up")

        with session_scope() as s:
            old_version = s.query(Meta).first()
            # TODO Check version for potential migration here?
            if not old_version:
                version = Meta(version=__version__)
                s.add(version)
                s.commit()

            # Initialize config

            config = s.query(Config).first()
            if config and config.config_json:
                config_json = config.config_json
            else:
                config_json = '{}'
                config = Config(config_json=config_json)
                s.add(config)
        self.config = CrackomaticConfig(json.loads(config_json))

        self._job_lock = Lock()
        self._job = None

        if with_cronjob:
            self._cron_thread_running = False
            self._cron_thread = Thread(
                daemon=True,  # Daemon mode so CTRL-C works
                target=self.check_scheduled_audits,
            )
            self._cron_thread.start()

    def clean_up_after_job(self, audit_uuid):
        """Clear Job object and possibly reschedule the audit"""
        try:
            delta = {
                AuditFrequency.DAILY: timedelta(days=1),
                AuditFrequency.WEEKLY: timedelta(days=7),
                AuditFrequency.MONTHLY: timedelta(days=30),
                AuditFrequency.QUARTERLY: timedelta(days=90),
                AuditFrequency.YEARLY: timedelta(days=365),
            }
            with session_scope() as s:
                old_audit = s.query(Audit).filter(
                    (Audit.uuid == audit_uuid)
                ).one()
                old_audit.report = self._job.report
                dct = {}
                # Copy audit if reschedule necessary
                if old_audit.frequency in delta:
                    # Copy these attributes
                    for attr in [
                        'user',
                        'domain',
                        'password',
                        'ldap_url',
                        'ca_file',
                        'dc_ip',
                        'email_field',
                        'user_filter',
                        'admin_filter',
                        'subject',
                        'message',
                        'include_cracked',
                        'frequency',
                    ]:
                        dct[attr] = getattr(old_audit, attr)
                    new_audit = Audit(
                        **dct,
                        uuid=uuid4().hex,
                        state=AuditState.SCHEDULED,
                        start=old_audit.start + delta[old_audit.frequency],
                    )
                    s.add(new_audit)
        except Exception as e:
            log.error("Rescheduling failed, audit id: %s" % audit_uuid)
            log.exception(e)
        finally:
            self._job = None

    def clean_up(self):
        """Clean up when application exits: terminate threads, etc."""
        if self._job:
            log.info("Shutting down, waiting for job to finish...")
            self._job_lock.acquire()
        self._cron_thread_running = False
        sleep(1)  # wait for db to shut down

    def add_audit(self, values):
        errs = self.config.get_errors()
        if sum(errs.values()):
            raise RuntimeError("Configuration contains errors: %s" % str(errs))
        values['frequency'] = int(values['frequency'])
        password = None
        state = AuditState.SCHEDULED
        if (values['frequency'] == AuditFrequency.JUST_ONCE
                and not values['start']):
            password = values['password']
            del values['password']
        if values['start']:
            values['start'] = dt.strptime(
                values['start'],
                '%Y-%m-%d %H:%M:%S',
            )
        else:
            values['start'] = None
        values['end'] = None
        values['include_cracked'] = (
            'include_cracked' in values and
            values['include_cracked'] == 'y'
        )
        audit_uuid = uuid4().hex
        with session_scope() as s:
            audit = Audit(**dict(**values), state=state, uuid=audit_uuid)
            s.add(audit)
            audit = freeze(audit)
        if password:
            # Start right away
            if self._job:
                with session_scope() as s:
                    audit = s.query(Audit).filter(
                        (Audit.uuid == audit_uuid)
                    ).one()
                    audit.state = AuditState.FAILED
                raise RuntimeError(
                    "Cracker is already running, can't start job for"
                    " unscheduled audit with ID %s" % audit_uuid
                )
            self._start_job(audit, password=password)
        return audit_uuid

    def delete_audit(self, audit_uuid):
        with session_scope(expire_on_commit=False) as s:
            s.query(Audit).filter(
                (Audit.uuid == audit_uuid)
            ).delete()

    def update_audit_state(self, audit):
        with session_scope(expire_on_commit=False) as s:
            db_audit = s.query(Audit).filter(
                (Audit.uuid == audit.uuid)
            ).one()
            db_audit.state = audit.state
            db_audit.start = audit.start
            db_audit.end = audit.end

    def _start_job(self, audit, password=None):
        errs = self.config.get_errors()
        if sum(errs.values()):
            log.error("Can't start job for audit with ID %s "
                      "because of errors: %s" % (audit.uuid, str(errs)))
            return
        log.info("Starting job for audit with ID %s" % audit.uuid)
        self._job = Job(
            audit,
            self._job_lock,
            self.config['cracker'],
            self.config['email'],
            cb_update=self.update_audit_state,
            cb_cleanup=self.clean_up_after_job,
            password=password,
        )
        self._job.start()

    def check_scheduled_audits(self):
        self._cron_thread_running = True
        while self._cron_thread_running:
            sleep(1)
            try:
                audits = self.get_scheduled_audits()
                if not audits or self._job:
                    continue
                audit = audits[0]
                if audit.start < dt.now():
                    self._start_job(audit)
            except Exception as e:
                log.error(str(e))
                log.exception(e)

    def get_log(self):
        result = ''
        with session_scope(expire_on_commit=False) as s:
            events = s.query(Log)
            for e in events:
                result += ("%s - %s - %s - %s\n" % (
                    e.created_at,
                    e.level,
                    e.logger,
                    e.msg,
                ))
                if e.trace:
                    result += "%s" % e.trace
        return result

    def update_config(self, section, dct):
        self.config.update(section, dct)
        with session_scope() as s:
            config = s.query(Config).one()
            config.config_json = self.config.to_json()

    def get_event_count(self):
        with session_scope(expire_on_commit=False) as s:
            count = int(s.query(func.count(Log.id)).scalar())
        return count

    def get_events(self, start, end):
        with session_scope(expire_on_commit=False) as s:
            events = s.query(Log).slice(start, end)
            # The content of these objects must be stored in plain
            # dictionary of strings, so the session object is not used
            # accross threads
            result = [freeze(e) for e in events]
        return result

    def get_report_and_audit(self, audit_uuid):
        with session_scope(expire_on_commit=False) as s:
            audit = s.query(Audit).filter(
                (Audit.uuid == audit_uuid)
            ).one()
            report = freeze(audit.report)
            audit = freeze(audit)
        audit.password = '***'
        return report, audit

    def _prepare_audit(self, audit):
        """Ensure all fields are human readable """
        audit = freeze(audit)
        audit.update({'state': AuditState(audit.state)})
        audit.update({'frequency': AuditFrequency(audit.frequency)})
        return audit

    def get_past_audits(self):
        with session_scope(expire_on_commit=False) as s:
            audits = s.query(Audit).filter(
                (Audit.state.in_(map(int, FINISHED_STATES)))
            ).order_by(Audit.end.desc()).all()
            audits = [self._prepare_audit(a) for a in audits]
        return audits

    def get_scheduled_audits(self):
        with session_scope(expire_on_commit=False) as s:
            audits = s.query(Audit).filter(
                Audit.state == AuditState.SCHEDULED
            ).order_by(Audit.start.asc()).all()
            audits = [self._prepare_audit(a) for a in audits]
        return audits

    def _get_last_audit_stats(self):
        with session_scope(expire_on_commit=False) as s:
            audits = s.query(Audit).filter(
                (Audit.state == int(AuditState.FINISHED))
            ).order_by(Audit.end.desc()).all()
            if audits:
                audit = audits[0]
                duration = audit.end - audit.start
                duration = format_timedelta(duration, format='short')
                since = dt.now() - audit.end
                since = format_timedelta(since, format='short')
                total_hashes = audit.report.total_hashes
                cracked = int(audit.report.cracked*total_hashes)
                dupes = json.loads(audit.report.cliques)
                dupes = sum([int(k)*v for k, v in dupes.items()])
            else:
                return {}

        return dict(
            title="Last Audit",
            tiles=[
                dict(
                    title=duration,
                    subtitle="Duration",
                ),
                dict(
                    title=since,
                    subtitle="Time since",
                ),
                dict(
                    title=total_hashes,
                    subtitle="Total hashes",
                ),
                dict(
                    title=cracked,
                    subtitle="Hashes cracked",
                ),
                dict(
                    title=dupes,
                    subtitle="Non-unique passwords",
                ),
            ],
        )

    def _get_idle_status_tiles(self):
        next_audit = self.get_scheduled_audits()
        if next_audit:
            next_audit = next_audit[-1]
            next_audit = next_audit.start - dt.now()
            next_audit = format_timedelta(next_audit, format='short')
        else:
            next_audit = '∞'
        tiles = [
            dict(
                title="Ready",
                subtitle="State",
                color='success',
            ),
            dict(
                title=next_audit,
                subtitle="Time of next audit",
            ),
        ]
        return tiles

    def _get_busy_status_tiles(self):
        j = self._job
        tiles = [
            dict(
                title="Running",
                subtitle="State",
                color='danger',
            ),
            dict(
                title=j.audit.state.name.replace('_', ' '),
                subtitle="Stage",
            ),
        ]
        if j.audit.state == AuditState.CRACKING and j.cracker:
            status = j.cracker.get_status()
            if isinstance(status, str):
                tiles += [
                    dict(
                        title="Status",
                        subtitle=status,
                    ),
                ]
                return tiles
            elif not isinstance(status, dict):
                tiles += [
                    dict(
                        title="Error",
                        subtitle="Could not determine cracker status",
                        color='danger',
                    ),
                ]
                return tiles
            speed = status['speed']
            if speed > 10**9:
                speed = "%.01fG" % (speed/10**9)
            elif speed > 10**6:
                speed = "%.01fM" % (speed/10**6)
            elif speed > 10**3:
                speed = "%.01fK" % (speed/10**3)
            else:
                speed = str(speed)
            started = dt.now() - j.audit.start
            started = format_timedelta(started, format='short')
            eta = status['ETA'] - dt.now()
            eta = format_timedelta(eta, format='short')
            tiles += [
                dict(
                    title=speed,
                    subtitle="Hashes/Second",
                    rumble=True,
                ),
                dict(
                    title=status['guesses'],
                    subtitle="Successful guesses",
                ),
                dict(
                    title='%d%%' % int(status['progress']),
                    subtitle="Progress",
                ),
                dict(
                    title=started,
                    subtitle="Started",
                ),
                dict(
                    title=eta,
                    subtitle="ETA",
                ),
            ]
        return tiles

    def get_status(self):
        try:
            if not self._job or self._job.audit.state in FINISHED_STATES:
                tiles = self._get_idle_status_tiles()
            else:
                tiles = self._get_busy_status_tiles()
        except Exception as e:
            log.exception(e)
            tiles += [
                dict(
                    title="Error",
                    subtitle="Could not determine current status",
                    color='danger',
                ),
            ]
        current = dict(
            title="Current",
            tiles=tiles,
        )
        last_audit = self._get_last_audit_stats()

        if last_audit:
            return [current, last_audit]
        return [current]
