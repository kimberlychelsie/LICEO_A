"""Explicit grading-policy loading and side-effect-free final-grade calculation."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import os
import re
from typing import Iterable, Mapping, Optional, Union


Number = Union[Decimal, int, float, str]
_ORDINAL_RE = re.compile(r"^(\d+)(?:st|nd|rd|th)$", re.IGNORECASE)


class GradingPolicyError(RuntimeError):
    """Base error for policy configuration failures."""


class MissingGradingPolicyError(GradingPolicyError):
    pass


class AmbiguousGradingPolicyError(GradingPolicyError):
    pass


class InvalidGradingPolicyError(GradingPolicyError):
    pass


@dataclass(frozen=True)
class GradingPolicy:
    policy_id: int
    branch_id: int
    year_id: int
    policy_version: str
    rounding_mode: str
    rounding_scale: int
    status: str
    required_periods: tuple[str, ...]


@dataclass(frozen=True)
class PeriodGrade:
    period_name: str
    grade: Optional[Number]
    completed: bool = True
    source_id: object = None


@dataclass(frozen=True)
class FinalGradeResult:
    policy_id: int
    policy_version: str
    required_periods: tuple[str, ...]
    final_grade: Optional[Decimal]
    complete: bool
    missing_periods: tuple[str, ...] = ()
    duplicate_periods: tuple[str, ...] = ()
    unexpected_periods: tuple[str, ...] = ()
    invalid_periods: tuple[str, ...] = ()
    error_code: Optional[str] = None


def grading_policy_final_grades_enabled() -> bool:
    """Allow an explicit emergency rollback while keeping integration on by default."""
    return os.getenv("GRADING_POLICY_FINAL_GRADES_ENABLED", "true").strip().lower() in {
        "1", "true", "yes", "on"
    }


def load_effective_grading_policy(
    cursor, *, branch_id: int, year_id: int
) -> Optional[GradingPolicy]:
    """Return the configured policy when integration is enabled.

    Disabled means legacy callers keep their existing behavior. Enabled means
    configuration is mandatory: missing, duplicate, or invalid policies raise
    instead of silently falling back to a global period count.
    """
    if not grading_policy_final_grades_enabled():
        return None
    return load_active_grading_policy(cursor, branch_id=branch_id, year_id=year_id)


def required_grading_periods(
    cursor, *, branch_id: int, year_id: int, legacy_periods: Iterable[str]
) -> tuple[str, ...]:
    policy = load_effective_grading_policy(
        cursor, branch_id=branch_id, year_id=year_id
    )
    if policy is not None:
        return policy.required_periods
    return tuple(_canonical_period_name(name) for name in legacy_periods)


def validate_required_period(value: object, required_periods: Iterable[str]) -> str:
    """Return a canonical period only when it belongs to the applicable policy."""
    period = _canonical_period_name(value)
    configured = tuple(_canonical_period_name(name) for name in required_periods)
    if period not in configured:
        raise InvalidGradingPolicyError(
            f"Grading period {period!r} is not part of the applicable policy."
        )
    return period


def validate_academic_term_name(
    value: object, required_periods: Iterable[str], *, allow_full_year: bool = True
) -> Optional[str]:
    """Validate schedule/subject term labels against the applicable policy."""
    name = str(value or "").strip()
    if not name:
        return None
    if allow_full_year and name.lower() in {"full year", "full term", "full_year", "full_term"}:
        return "Full Year"
    period_value = re.sub(r"\s+term$", "", name, flags=re.IGNORECASE).strip()
    return f"{validate_required_period(period_value, required_periods)} Term"


def _row_value(row, key, index):
    if isinstance(row, Mapping):
        return row[key]
    return row[index]


def _canonical_period_name(value: object) -> str:
    name = str(value or "").strip().lower()
    match = _ORDINAL_RE.fullmatch(name)
    if not match:
        raise InvalidGradingPolicyError(f"Invalid grading period name: {value!r}")
    number = int(match.group(1))
    if number <= 0:
        raise InvalidGradingPolicyError(f"Invalid grading period name: {value!r}")
    suffix = "th" if 10 <= number % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")
    canonical = f"{number}{suffix}"
    if name != canonical:
        raise InvalidGradingPolicyError(f"Noncanonical grading period name: {value!r}")
    return canonical


def load_active_grading_policy(cursor, *, branch_id: int, year_id: int) -> GradingPolicy:
    """Load exactly one valid active policy and its ordered calendar periods."""
    cursor.execute(
        """
        SELECT policy_id, branch_id, year_id, policy_version,
               rounding_mode, rounding_scale, status
        FROM grading_policies
        WHERE branch_id=%s AND year_id=%s AND status='active'
        ORDER BY policy_id
        """,
        (branch_id, year_id),
    )
    rows = cursor.fetchall() or []
    if not rows:
        raise MissingGradingPolicyError(
            f"No active grading policy for branch {branch_id}, year {year_id}."
        )
    if len(rows) != 1:
        raise AmbiguousGradingPolicyError(
            f"Multiple active grading policies for branch {branch_id}, year {year_id}."
        )

    row = rows[0]
    policy_id = int(_row_value(row, "policy_id", 0))
    cursor.execute(
        """
        SELECT gpp.sequence_no, gpr.period_name
        FROM grading_policy_periods gpp
        JOIN grading_period_ranges gpr
          ON gpr.id=gpp.calendar_term_id
         AND gpr.branch_id=gpp.branch_id
         AND gpr.year_id=gpp.year_id
        WHERE gpp.policy_id=%s
        ORDER BY gpp.sequence_no
        """,
        (policy_id,),
    )
    period_rows = cursor.fetchall() or []
    sequences = [int(_row_value(item, "sequence_no", 0)) for item in period_rows]
    if not sequences or sequences != list(range(1, len(sequences) + 1)):
        raise InvalidGradingPolicyError(
            f"Policy {policy_id} does not have contiguous periods starting at 1."
        )
    required = tuple(
        _canonical_period_name(_row_value(item, "period_name", 1))
        for item in period_rows
    )
    if len(set(required)) != len(required):
        raise InvalidGradingPolicyError(f"Policy {policy_id} contains duplicate periods.")

    rounding_mode = str(_row_value(row, "rounding_mode", 4))
    rounding_scale = int(_row_value(row, "rounding_scale", 5))
    if rounding_mode != "excel_round" or not 0 <= rounding_scale <= 4:
        raise InvalidGradingPolicyError(f"Policy {policy_id} has unsupported rounding.")

    return GradingPolicy(
        policy_id=policy_id,
        branch_id=int(_row_value(row, "branch_id", 1)),
        year_id=int(_row_value(row, "year_id", 2)),
        policy_version=str(_row_value(row, "policy_version", 3)),
        rounding_mode=rounding_mode,
        rounding_scale=rounding_scale,
        status=str(_row_value(row, "status", 6)),
        required_periods=required,
    )


def _valid_grade(value: Optional[Number]) -> Optional[Decimal]:
    if value is None or isinstance(value, bool):
        return None
    try:
        grade = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if not grade.is_finite() or grade < 0 or grade > 100:
        return None
    return grade


def calculate_final_grade(
    policy: GradingPolicy, period_grades: Iterable[PeriodGrade]
) -> FinalGradeResult:
    """Calculate a final grade without mutating policy or grade records."""
    if policy.status != "active":
        raise InvalidGradingPolicyError("Final grades require an active grading policy.")
    if not policy.required_periods or len(set(policy.required_periods)) != len(policy.required_periods):
        raise InvalidGradingPolicyError("Required periods must be nonempty and unique.")
    if policy.rounding_mode != "excel_round" or not 0 <= policy.rounding_scale <= 4:
        raise InvalidGradingPolicyError("Unsupported final-grade rounding policy.")

    required = tuple(_canonical_period_name(name) for name in policy.required_periods)
    supplied = list(period_grades)
    grouped = {}
    invalid_names = []
    for item in supplied:
        try:
            name = _canonical_period_name(item.period_name)
        except InvalidGradingPolicyError:
            invalid_names.append(str(item.period_name))
            continue
        grouped.setdefault(name, []).append(item)

    duplicates = tuple(name for name in required if len(grouped.get(name, ())) > 1)
    unexpected = tuple(sorted(name for name in grouped if name not in required))
    missing = []
    invalid = list(invalid_names)
    values = []
    for name in required:
        entries = grouped.get(name, ())
        if not entries:
            missing.append(name)
            continue
        if len(entries) != 1:
            continue
        entry = entries[0]
        value = _valid_grade(entry.grade) if entry.completed else None
        if value is None:
            invalid.append(name)
        else:
            values.append(value)

    error_code = None
    if duplicates:
        error_code = "duplicate_period_grades"
    elif unexpected:
        error_code = "unexpected_period_grades"
    elif invalid:
        error_code = "invalid_or_incomplete_period_grades"
    elif missing:
        error_code = "missing_period_grades"

    if error_code:
        return FinalGradeResult(
            policy.policy_id, policy.policy_version, required, None, False,
            tuple(missing), duplicates, unexpected, tuple(invalid), error_code,
        )

    mean = sum(values, Decimal("0")) / Decimal(len(required))
    quantum = Decimal("1").scaleb(-policy.rounding_scale)
    final = mean.quantize(quantum, rounding=ROUND_HALF_UP)
    return FinalGradeResult(
        policy.policy_id, policy.policy_version, required, final, True
    )
