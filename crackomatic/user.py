from logging import getLogger
import getpass
import sys

from flask_login import UserMixin
from argon2 import PasswordHasher
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import IntegrityError

from .models import session_scope, LocalUser, freeze
from .ldap import ldap_query


log = getLogger(__name__)


class User(UserMixin):
    logged_in_users = {}

    def authenticate(username, password, auth_config):
        """Return a User() object if authentication succeeds

        Username is assumed to be local first, if unsuccessful LDAP
        authentication will be performed.
        """
        authenticated = User.authenticate_local(username, password)
        if not authenticated and auth_config:
            authenticated = User.authenticate_ldap(
                username, password, auth_config
            )
        if authenticated:
            log.info("Successful authentication: %s" % username)
            user = User()
            user.id = username
            User.logged_in_users[user.id] = user
            return user
        else:
            log.error("Failed authentication: %s" % username)
        return None

    def authenticate_ldap(username, password, auth_config):
        """Return True iff LDAP authentication suceeds"""
        log.debug('Querying LDAP for authentication')
        url = auth_config['ldap_url']
        ca_file = auth_config['ca_file']
        basedn = auth_config['basedn']
        search_filter = auth_config['filter']
        try:
            # prevent ldap injection
            # If someone has a weird username, too bad
            assert not set(username).intersection(set('&%@,=()"\'')), \
                    'username rejected'
            binddn = auth_config['binddn'] % username
            result = ldap_query(url, basedn, ca_file, binddn, password,
                                search_filter)
            return binddn in result
        except Exception as e:
            log.exception(e)
        return False

    def authenticate_local(username, password):
        """Return True iff authentication against local DB suceeds"""
        with session_scope() as s:
            try:
                user = s.query(LocalUser).filter(
                    LocalUser.username == username
                ).one()
            except NoResultFound:
                user = None
            ph = PasswordHasher()
            if user:
                if ph.verify(user.password, password):
                    return True
            else:
                # Prevent timing attacks
                ph.hash('')
        return False

    def create(username, password):
        ph = PasswordHasher()
        hash = ph.hash(password)
        with session_scope() as s:
            user = LocalUser(
                username=username,
                password=hash,
            )
            s.add(user)
        log.info("Created local user '%s'" % username)

    def list():
        with session_scope() as s:
            users = s.query(LocalUser)
            users = [freeze(u) for u in users]
            return [u.username for u in users]

    def delete(username):
        with session_scope() as s:
            user = s.query(LocalUser).filter(
                LocalUser.username == username
            ).one()

            s.delete(user)
        log.info("Deleted local user '%s'" % username)

    def change_password(username, password):
        with session_scope() as s:
            user = s.query(LocalUser).filter(
                LocalUser.username == username
            ).one()

            ph = PasswordHasher()
            hash = ph.hash(password)
            user.password = hash
        log.info("Changed password for local user '%s'" % username)


def get_password():
    min_chars = 12
    password1 = getpass.getpass(prompt='Password: ', stream=None)
    password2 = getpass.getpass(prompt='Repeat: ', stream=None)
    if password1 != password2:
        print("Passwords don't match")
        sys.exit(1)
    if len(password1) < min_chars:
        print("Passwords must be at least %d characters long" % min_chars)
        sys.exit(1)
    return password1


def perform_user_action(action, username):
    if action != 'list' and not username:
        print("You must supply a user name as an argument")
        sys.exit(1)
    try:
        if action == 'add':
            password = get_password()
            User.create(username, password)
        elif action == 'delete':
            User.delete(username)
        elif action == 'change':
            password = get_password()
            User.change_password(username, password)
        elif action == 'list':
            for u in User.list():
                print(u)
        else:
            log.error("Invalid action: %s" % action)
    except IntegrityError:
        log.error("User already exists: %s" % username)
    except NoResultFound:
        log.error("User not found: %s" % username)
