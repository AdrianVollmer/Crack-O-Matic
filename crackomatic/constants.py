from enum import IntEnum, auto


class AuditFrequency(IntEnum):
    JUST_ONCE = auto()
    DAILY = auto()
    WEEKLY = auto()
    MONTHLY = auto()
    QUARTERLY = auto()
    YEARLY = auto()


class AuditState(IntEnum):
    SCHEDULED = auto()
    REPLICATING = auto()
    CRACKING = auto()
    ANALYZING = auto()
    SENDING_EMAILS = auto()
    ABORTED = auto()
    FAILED = auto()
    FINISHED = auto()


FINISHED_STATES = [
    AuditState.FINISHED,
    AuditState.ABORTED,
    AuditState.FAILED,
]
