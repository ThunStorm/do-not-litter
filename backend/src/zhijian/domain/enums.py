from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    NEEDS_USER = "NEEDS_USER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class JobType(StrEnum):
    RECRUITMENT = "RECRUITMENT"
    TRAVEL = "TRAVEL"
    UNKNOWN = "UNKNOWN"


class ContentType(StrEnum):
    RECRUITMENT = "RECRUITMENT"
    TRAVEL = "TRAVEL"
    UNSUPPORTED = "UNSUPPORTED"


class ResolutionStatus(StrEnum):
    CANDIDATE = "CANDIDATE"
    CONFIRMED = "CONFIRMED"
    REVIEW = "REVIEW"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"


class UserState(StrEnum):
    DISCOVERED = "DISCOVERED"
    SAVED = "SAVED"
    PLANNED = "PLANNED"
    VISITED = "VISITED"
    DISMISSED = "DISMISSED"


class EligibilityStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    REVIEW = "REVIEW"
