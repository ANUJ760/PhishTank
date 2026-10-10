"""Placement extraction must follow the upload's layout, not model guesses."""
from backend.intake.pdf_timetable import extract_pdf_timetable, overlaps_rule


def row(*cells):
    line = ''
    for column, value in cells:
        line = line.ljust(column) + value
    return line


def timetable(professor='Dr. Lina Rivera', code='CS000101'):
    return '\n'.join([
        row((0, 'TIME/DAY'), (24, '09:00 - 10:00'), (64, '10:00 - 11:00'), (104, '11:00 - 12:00')),
        row((0, 'MONDAY'), (24, code)),
        '',
        row((0, 'TUESDAY'), (64, code)),
        '', '', '',
        row((0, 'Course Code'), (30, 'Course'), (70, 'Coordinator')),
        row((0, code), (30, 'Applied Optics'), (70, professor)),
    ])


def test_positions_and_faculty_come_from_each_upload():
    for teacher, code in [('Dr. Lina Rivera', 'CS000101'), ('Prof. Kenji Nakamura', 'CS000202')]:
        result = extract_pdf_timetable(timetable(teacher, code), [teacher])
        assert [(c.day, c.start, c.end, c.course_code, c.teachers) for c in result.classes] == [
            ('Monday', '09:00', '10:00', code, [teacher]),
            ('Tuesday', '10:00', '11:00', code, [teacher]),
        ]


def test_conflict_checks_use_clock_intersection_and_actual_teacher():
    placement = extract_pdf_timetable(timetable(), ['Dr. Lina Rivera']).classes[0]
    params = {'teacher': 'Dr. Lina Rivera', 'day': 0, 'slots': [0]}
    assert overlaps_rule(placement, 'teacher_unavailable', params, ['09:00', '10:00'])
    assert not overlaps_rule(placement, 'teacher_unavailable', {**params, 'slots': [1]}, ['09:00', '10:00'])
    assert not overlaps_rule(placement, 'teacher_unavailable', {**params, 'teacher': 'Prof. Rao'}, ['09:00', '10:00'])


def test_missing_grid_does_not_claim_placements():
    result = extract_pdf_timetable('Faculty: Dr. Lina Rivera', ['Dr. Lina Rivera'])
    assert result.classes == []
    assert result.warnings


def test_unknown_course_does_not_borrow_another_professor():
    text = timetable().replace(row((0, 'MONDAY'), (24, 'CS000101')), row((0, 'MONDAY'), (24, 'CS999999')))
    result = extract_pdf_timetable(text, ['Dr. Lina Rivera'])
    assert result.classes[0].teachers == []
    assert result.warnings
