import logging
import traceback


class SQLHandler(logging.Handler):
    # A very basic logger that commits a LogRecord to the SQL Db
    # https://docs.pylonsproject.org/projects/pyramid-cookbook/en/latest/logging/sqlalchemy_logger.html

    def emit(self, record):
        from .models import session_scope, Log
        trace = None
        exc = record.__dict__['exc_info']
        if exc:
            trace = traceback.format_exc()
        with session_scope() as s:
            log = Log(
                logger=record.__dict__['name'],
                level=record.__dict__['levelname'],
                trace=trace,
                msg=str(record.__dict__['msg']),)
            s.add(log)


def init_log(level=logging.INFO, sql=False):
    # create logger
    # Don't use the root logger, or else all other modules such as werkzeug
    # will use this one too.
    logger = logging.getLogger('crackomatic')
    logger.setLevel(level)

    # create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # create console handler and set level to debug
    ch = logging.StreamHandler()
    ch.setLevel(level)

    # add formatter to ch
    ch.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(ch)

    # Shut up sqlalchemy
    logging.getLogger('sqlalchemy').setLevel(logging.WARN)
    logging.getLogger('sqlalchemy').addHandler(ch)

    if sql:
        # create SQL handler and set level to debug
        sh = SQLHandler()
        sh.setLevel(logging.INFO)
        sh.setFormatter(formatter)
        logger.addHandler(sh)
