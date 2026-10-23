from pathlib import Path

import pytest
from werkzeug.datastructures import MultiDict

from routes.student_portal import (
    _completed_education_levels,
    _validate_swafo_personal_info,
    _validate_swafo_submission,
)


def test_swafo_draft_normalizes_and_accepts_valid_rows():
    form = MultiDict([
        ("nickname", "  KC  "),
        ("uri_ng_kabuhayan", "Katamtaman"),
        ("kalagayan_pag_aaral", "Mahusay"),
        ("fm_name[]", "Juan Dela Cruz"),
        ("fm_edad[]", "40"),
        ("fm_estatus[]", "College"),
        ("fm_pinapasukan[]", "Liceo"),
        ("fm_trabaho[]", "Teacher"),
        ("ed_antas[]", "Elementary"),
        ("ed_paaralan[]", "Liceo"),
        ("ed_taon[]", "2020"),
        ("ed_katamo[]", "With Honors"),
    ])

    cleaned, family, education, summer = _validate_swafo_submission(form)

    assert cleaned["nickname"] == "KC"
    assert family == [{
        "name": "Juan Dela Cruz", "edad": "40", "estatus": "College",
        "pinapasukan": "Liceo", "trabaho": "Teacher",
    }]
    assert education[0]["taon"] == "2020"
    assert summer == []


@pytest.mark.parametrize("field,value", [
    ("uri_ng_kabuhayan", "Unknown"),
    ("kalagayan_pag_aaral", "Excellent"),
])
def test_swafo_rejects_tampered_choices(field, value):
    with pytest.raises(ValueError):
        _validate_swafo_submission(MultiDict([(field, value)]))


def test_swafo_rejects_invalid_family_age_and_education_year():
    with pytest.raises(ValueError):
        _validate_swafo_submission(MultiDict([
            ("fm_name[]", "Juan"), ("fm_edad[]", "121"),
        ]))

    with pytest.raises(ValueError):
        _validate_swafo_submission(MultiDict([
            ("ed_antas[]", "Elementary"), ("ed_paaralan[]", "Liceo"),
            ("ed_taon[]", "20x6"),
        ]))


def test_swafo_submit_requires_yes_no_answers():
    with pytest.raises(ValueError, match="Pumili ng sagot"):
        _validate_swafo_submission(MultiDict(), require_complete=True)


def test_swafo_template_contains_prefilled_personal_information():
    template = Path("templates/student_swafo_form.html").read_text(encoding="utf-8")
    for label in ("Buong Pangalan", "Palayaw", "Edad", "Kasarian", "Kapanganakan: Petsa",
                  "Kapanganakan: Lugar", "Tirahan", "Cell Number"):
        assert label in template
    assert 'name="nickname"' in template
    assert "student_info.contact_number" in template


def test_swafo_personal_info_is_validated_and_normalized():
    personal = _validate_swafo_personal_info(MultiDict({
        "student_first_name": " Maria ", "student_middle_name": "Santos",
        "student_last_name": "Dela Cruz", "gender": "Female", "dob": "2010-05-12",
        "birthplace": "Majayjay, Laguna", "address": "Barangay San Roque, Majayjay",
        "contact_number": "09123456789",
    }))
    assert personal["student_first_name"] == "Maria"
    assert personal["contact_number"] == "09123456789"

    with pytest.raises(ValueError):
        _validate_swafo_personal_info(MultiDict({
            "student_first_name": "M", "student_last_name": "Student", "gender": "Female",
            "dob": "2030-01-01", "birthplace": "Laguna", "address": "Valid address",
        }))


@pytest.mark.parametrize(("grade_level", "expected"), [
    ("Nursery", []),
    ("Kinder", []),
    ("Grade 3", ["Kinder"]),
    ("Grade 7", ["Kinder", "Elementary"]),
    ("Grade 11", ["Kinder", "Elementary", "Junior High"]),
])
def test_completed_education_levels_follow_current_grade(grade_level, expected):
    assert _completed_education_levels(grade_level) == expected
