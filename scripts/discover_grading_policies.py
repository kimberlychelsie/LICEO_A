"""Read-only grading-policy discovery report; performs no schema or data writes."""

import json
import os
import sys

import psycopg2
import psycopg2.extras


def connect():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.environ["DB_NAME"],
        user=os.getenv("DB_USER", "liceo_db"),
        password=os.getenv("DB_PASSWORD", "1234"),
        connect_timeout=5,
    )


def discover(cursor):
    cursor.execute(
        """
        SELECT b.branch_id, b.branch_name, sy.year_id, sy.label AS school_year,
               sy.is_active,
               COALESCE((
                   SELECT json_agg(json_build_object(
                       'id', r.id, 'name', r.period_name,
                       'start_date', r.start_date, 'end_date', r.end_date
                   ) ORDER BY r.start_date, r.id)
                   FROM grading_period_ranges r
                   WHERE r.branch_id=b.branch_id AND r.year_id=sy.year_id
               ), '[]'::json) AS calendar_terms,
               COALESCE((
                   SELECT json_agg(p ORDER BY p)
                   FROM (SELECT DISTINCT pg.grading_period AS p
                         FROM posted_grades pg
                         JOIN sections sec ON sec.section_id=pg.section_id
                         WHERE pg.year_id=sy.year_id
                           AND sec.branch_id=b.branch_id) periods
               ), '[]'::json) AS posted_periods,
               COALESCE((
                   SELECT json_agg(p ORDER BY p)
                   FROM (SELECT DISTINCT gsr.grading_period AS p
                         FROM grade_submission_requests gsr
                         WHERE gsr.year_id=sy.year_id AND gsr.branch_id=b.branch_id
                           AND gsr.status IN (
                             'pending_academic_coordinator','pending_admin',
                             'approved_for_posting','posted','rejected'
                           )) periods
               ), '[]'::json) AS approved_periods,
               COALESCE((
                   SELECT json_agg(json_build_object(
                       'version', gp.policy_version, 'status', gp.status,
                       'rounding_mode', gp.rounding_mode,
                       'rounding_scale', gp.rounding_scale
                   ) ORDER BY gp.policy_id)
                   FROM grading_policies gp
                   WHERE gp.branch_id=b.branch_id AND gp.year_id=sy.year_id
               ), '[]'::json) AS policies
        FROM school_years sy
        JOIN branches b ON b.branch_id=sy.branch_id
        ORDER BY sy.label, b.branch_id
        """
    )
    return cursor.fetchall() or []


def main():
    if os.getenv("ALLOW_GRADING_POLICY_DISCOVERY", "").lower() not in {"1", "true", "yes"}:
        raise SystemExit("Set ALLOW_GRADING_POLICY_DISCOVERY=true to run this read-only report.")
    with connect() as conn:
        conn.set_session(readonly=True, autocommit=False)
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            report = discover(cursor)
        conn.rollback()
    json.dump(report, sys.stdout, default=str, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
