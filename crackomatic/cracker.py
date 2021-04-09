from datetime import datetime as dt, timedelta, date
import os
from threading import Thread, Lock
import time
import re
import signal
from subprocess import Popen, PIPE, run
from logging import getLogger

log = getLogger(__name__)


def get_cracker(engine, *args, **kwargs):
    engine = {'John': John, 'Hashcat': Hashcat}[engine]
    return engine(*args, **kwargs)


class Cracker(Thread):
    password_regex = ''

    def __init__(self, hash_file, wordlist, rules, bin_path,
                 root_dir='/tmp', args=[]):
        log.debug("Initializing cracker")
        self._run_lock = Lock()
        self._run_lock.acquire()
        super().__init__()
        self._hash_file = hash_file
        self._wordlist = wordlist
        self._rules = rules
        self._bin_path = bin_path
        self._args = args

        self._potfile = os.path.join(root_dir, 'potfile')

        self._process = None

        self.passwords = {}
        self.output = {
            'stdout': '',
            'stderr': '',
        }
        self.version = self._get_version()
        self.start()

    def abort(self):
        self._process.terminate()

    def wait_until_finished(self):
        self._run_lock.acquire()
        self._run_lock.release()

    def get_status(self):
        # Return None if process has not yet started or already finished
        if not self._process:
            return "Process hasn't started"
        elif self._process.returncode is not None:
            return "Process finished"
        return self._get_status()

    def _capture(self, stream, buffer):
        while self._process.returncode is None:
            data = stream.readline()
            if not re.match(self.password_regex, data):
                self.output[buffer] += data
            else:
                self.output[buffer] += "*** SENSITIVE DATA REMOVED ***\n"

    def _start_capture_threads(self):
        t_stdout = Thread(
            target=self._capture,
            args=(self._process.stdout, 'stdout')
        )
        t_stdout.start()
        t_stderr = Thread(
            target=self._capture,
            args=(self._process.stderr, 'stderr')
        )
        t_stderr.start()

    def run(self):
        try:
            cmd = self.command_line()
            log.debug("Running command: " + " ".join(cmd))
            self._process = Popen(
                cmd,
                stdin=PIPE,
                stdout=PIPE,
                stderr=PIPE,
                encoding='utf8',
                preexec_fn=lambda: os.nice(19),
            )

            self._start_capture_threads()
            self._process.wait()
            if not self._process.returncode == self.expected_returncode:
                log.error("Process failed with return code %d: %s" %
                          (self._process.returncode,
                           self.output['stderr'] or self.output['stdout']))
            else:
                log.debug("Process exited with return code 0: %s" %
                          self.output['stdout'])
            self.passwords = self._get_passwords()
        finally:
            try:
                os.remove(self._potfile)
            except OSError:
                pass
            finally:
                self._run_lock.release()


class Hashcat(Cracker):
    password_regex = '^[a-f0-9]{32}:.*$'
    expected_returncode = 1
    # 1 means 'exhausted', which is fine for a wordlist attack

    def command_line(self):
        return [
            self._bin_path,
            self._hash_file,
            '-m', '1000',
            '-a', '0',
            '--outfile-autohex-disable',
            '--status',
            '--machine-readable',
            '--potfile-path', self._potfile,
            '--rules-file', self._rules,
            self._wordlist,
            *self._args,
        ]

    def _get_passwords(self):
        command_line = [
            self._bin_path,
            self._hash_file,
            '-m', '1000',
            '--potfile-path', self._potfile,
            '--show',
            '--username',
        ]
        p = Popen(command_line, stdout=PIPE, encoding='utf8')
        result = {}
        output, err = p.communicate()
        for line in output.splitlines():
            if line and ':' in line:
                user, _, password = line.split(':')[:3]
                result[user] = password
            else:
                break
        return result

    def _get_version(self):
        output = run(
            [self._bin_path],
            stdout=PIPE,
            encoding='utf8',
        )
        return output.stdout

    def _get_status(self):
        # Status is printed periodically
        for line in reversed(self.output['stdout'].splitlines()):
            m = re.match(
                r'.*SPEED\s+(?P<speed>([0-9]+\s+)+)[A-Z_].*'
                r'PROGRESS\s+(?P<progress>[0-9]+)\s+(?P<remaining>[0-9]+)\s.*'
                r'RECHASH\s+(?P<rechash>[0-9]+)\s.*',
                line,
            )
            if m:
                guesses = int(m.groupdict()['rechash'])
                percentage = 100 * int(m.groupdict()['progress']) / \
                    (int(m.groupdict()['progress']) +
                     int(m.groupdict()['remaining']))
                speed = re.sub(r'\s+', ' ', m.groupdict()['speed'])
                factor = speed.split()[1::2]
                speed = speed.split()[::2]
                speed = sum(int(x1) * int(x2)/1000
                            for x1, x2 in zip(speed, factor))
                ETA = dt.now() + \
                    timedelta(seconds=int(m.groupdict()['remaining'])/speed)
                return {
                    'guesses': guesses,
                    'ETA': ETA,
                    'progress': percentage,
                    'speed': speed,
                }


class John(Cracker):
    # Make sure not to match this string:
    # Loaded X password hashes with no different salts (NT [MD4 ...])
    # We do this here by making a negative lookahead assertion for the
    # expression in the parenthesis.
    password_regex = r'^.* +\((?!NT \[MD4).*\) *$'
    expected_returncode = 0

    def command_line(self):
        cores = len(os.sched_getaffinity(0))
        cmd = [
            self._bin_path,
            self._hash_file,
            '--format=nt',
            '--pot=%s' % self._potfile,
            '--no-log',
            '--wordlist=%s' % self._wordlist,
            '--rules=%s' % self._rules,
            *self._args,
        ]
        if cores > 1:
            cmd.append('--fork=%d' % cores)
        return cmd

    def _get_version(self):
        output = run(
            [self._bin_path],
            stdout=PIPE,
            encoding='utf8',
        )
        version = re.search(r'version ([0-9.a-zA-Z_+-]+)\s', output.stdout)
        if version:
            version = version[1]
            if 'jumbo' not in version:
                raise RuntimeError("John is not the 'jumbo' version: %s"
                                   % version)
            return version

    def _get_status(self):
        # Save output length before we trigger status update
        lines_before = len(self.output['stderr'].splitlines())

        # Sending SIGUSR1 to all threads will trigger status update
        ps_output = run(
            ['ps', '-opid', '--no-headers', '--ppid',
             str(self._process.pid)],
            stdout=PIPE,
            encoding='utf8',
        )
        child_pids = [int(line) for line in ps_output.stdout.splitlines()]
        for p in child_pids:
            os.kill(p, signal.SIGUSR1)
        self._process.send_signal(10)

        # Wait until the status update made its way to the output buffer
        time.sleep(1)

        ETA = []
        percentage = []
        speed = []
        guesses = []
        factors = {'K': 10**3, 'M': 10**6, 'G': '10**9', '': 1}

        # Parse each line that got added since we triggered the status
        # update; each thread has added one line
        for line in self.output['stderr'].splitlines()[lines_before:]:
            m = re.match(
                r'.*(^|\s)(?P<guesses>[0-9]+)g '
                r'[0-9:]+ (?P<percentage>[0-9.]+)% '
                r'\(ETA: (?P<ETA>[0-9: -]+)\).*'
                r' (?P<speed>[0-9.]+)(?P<factor>[KMG]?)p/s.*',
                line,
            )
            if m:
                guesses.append(int(m.groupdict()['guesses']))
                eta = m.groupdict()['ETA']
                if '-' in eta:
                    eta = dt.strptime(eta, '%Y-%m-%d %H:%M')
                else:
                    eta = dt.combine(
                        date.today(),
                        dt.strptime(eta, '%H:%M:%S').time(),
                    )
                ETA.append(eta)
                percentage.append(float(m.groupdict()['percentage']))
                factor = factors[m.groupdict()['factor']]
                speed.append(float(m.groupdict()['speed'])*factor)
        if guesses and ETA and percentage and speed:
            return {
                'guesses': sum(guesses),
                'ETA': max(ETA),
                'progress': sum(percentage)/len(percentage),
                'speed': sum(speed),
            }
        else:
            log.error(
                (
                    "Something went wrong:\nGuesses: %s\nETA: %s\n"
                    "Percentage: %s\nSpeed: %s"
                ) % (guesses, ETA, percentage, speed)
            )

    def _get_passwords(self):
        command_line = [
            self._bin_path,
            self._hash_file,
            '--format:nt',
            '--pot=%s' % self._potfile,
            '--show',
        ]
        p = Popen(command_line, stdout=PIPE, encoding='utf8')
        result = {}
        output, err = p.communicate()
        if not p.returncode == 0:
            log.error('Getting passwords failed with return code %d: %s'
                      % (p.returncode, err))
        for line in output.splitlines():
            if line and ':' in line:
                user, password = line.split(':')[:2]
                result[user] = password
            else:
                break
        return result
