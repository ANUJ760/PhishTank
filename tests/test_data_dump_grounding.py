"""Regressions for uploaded faculty being replaced by demo/parser output."""
from itertools import count

import pytest

from backend import config
from backend.intake import data_dump
from backend.llm.client import LLMError, call_json
from backend.models import Roster, Room, Session


@pytest.fixture
def isolated_intake(monkeypatch):
    roster = Roster(teachers=['Prof. Rao'], rooms=[Room(name='Demo Hall', capacity=30)],
                    sessions=[Session(id='DB_LAB', course='DB_LAB', teachers=['Prof. Rao'])])
    saved = []
    ids = count(1)
    monkeypatch.setattr(config, 'MOCK_LLM', True)
    monkeypatch.setattr(data_dump.db, 'get_roster', lambda: roster)
    monkeypatch.setattr(data_dump.db, 'latest_schedule', lambda: None)
    monkeypatch.setattr(data_dump.db, 'save_roster', lambda value: saved.append(value.model_copy(deep=True)))
    monkeypatch.setattr(data_dump.db, 'save_upload', lambda *args: None)
    monkeypatch.setattr(data_dump.db, 'save_rule', lambda *args: None)
    monkeypatch.setattr(data_dump.db, 'log_audit_event', lambda *args: None)
    monkeypatch.setattr(data_dump.db, 'next_rule_id', lambda: f'R{next(ids)}')
    return saved


@pytest.mark.parametrize('file_kind', ['csv', 'xlsx'])
def test_uploaded_professors_and_text_override_demo_context(isolated_intake, file_kind):
    rows = [
        ['Course Name', 'Professor', 'Room', 'Day', 'Slot'],
        ['Physics', 'Dr. Marie Curie', 'Science Hall', 'Wednesday', '3'],
        ['Computing', 'Dr. Alan Turing', 'Computer Lab', 'Thursday', '2'],
    ]
    if file_kind == 'csv':
        content = '\n'.join(','.join(row) for row in rows).encode()
    else:
        from io import BytesIO
        from openpyxl import Workbook
        book = Workbook()
        for row in rows:
            book.active.append(row)
        buffer = BytesIO()
        book.save(buffer)
        content = buffer.getvalue()
    result = data_dump.ingest_data_dump(
        files=[(f'timetable.{file_kind}', content)],
        notes='Dr. Marie Curie cannot teach on Wednesday afternoon.',
    )
    faculty = {e['name'] for e in result.entities if e['kind'] == 'faculty'}
    assert faculty == {'Dr. Marie Curie', 'Dr. Alan Turing'}
    unavailable = [r.params for r in result.rules if r.type == 'teacher_unavailable']
    assert unavailable == [{'teacher': 'Dr. Marie Curie', 'day': 2, 'slots': [3, 4, 5]}]
    qualifications = [r.params for r in result.rules if r.type == 'only_qualified']
    assert {'session_id': 'PHYSICS', 'teachers': ['Dr. Marie Curie']} in qualifications
    assert 'Prof. Rao' not in result.model_dump_json()
    assert 'Demo Hall' not in result.model_dump_json()
    # Registry preservation is independent of the upload's extraction context.
    assert 'Prof. Rao' in isolated_intake[-1].teachers


def test_availability_table_does_not_become_course_workload(isolated_intake):
    result = data_dump.ingest_data_dump(files=[('availability.csv',
        b'Faculty,Day,Slot,Status\nDr. Alan Turing,Tuesday,2,Unavailable')])
    assert len(result.rules) == 1
    assert result.rules[0].params == {'teacher': 'Dr. Alan Turing', 'day': 1, 'slots': [2]}
    assert not any(s.course == 'Tuesday' for s in isolated_intake[-1].sessions)


def test_llm_cannot_register_invented_professor(isolated_intake, monkeypatch):
    monkeypatch.setattr(data_dump, 'call_json', lambda **kwargs: data_dump.DataDumpLLMOut(
        summary='Invented Professor is unavailable',
        rules=[data_dump.ExtractedRuleDraft(type='teacher_unavailable',
            params={'teacher': 'Invented Professor', 'day': 0, 'slots': [0]})],
        entities=[data_dump.ExtractedEntity(name='Invented Professor', kind='faculty')],
    ))
    result = data_dump.ingest_data_dump(files=[], notes='Review the timetable.')
    assert result.rules == []
    assert 'Invented Professor' not in result.model_dump_json()
    assert 'Invented Professor' not in isolated_intake[-1].teachers


def test_mock_mode_honors_no_fixture_contract(monkeypatch):
    monkeypatch.setattr(config, 'MOCK_LLM', True)
    with pytest.raises(LLMError, match='mock responses are disabled'):
        call_json(fn='extract_data_dump', tier='intake', messages=[],
                  schema=data_dump.DataDumpLLMOut, fallback_to_mock=False)


def make_text_pdf(text):
    """Small valid PDF fixture containing caller-supplied text."""
    stream = f'BT /F1 12 Tf 30 750 Td ({text}) Tj ET'.encode()
    objects = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
        f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'\nendstream',
    ]
    pdf = b'%PDF-1.4\n'
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f'{index} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(pdf)
    pdf += b'xref\n0 6\n0000000000 65535 f \n'
    pdf += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets[1:])
    pdf += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    return pdf


@pytest.mark.parametrize('professor', ['Prof. P. R. Meshram', 'Dr. L. A. Rivera'])
def test_pdf_faculty_comes_from_uploaded_bytes(isolated_intake, professor):
    import shutil
    if not shutil.which('pdftotext'):
        pytest.skip('poppler-utils is required for PDF intake')
    result = data_dump.ingest_data_dump(
        files=[('user-selected-file.pdf', make_text_pdf(professor))],
        notes=f'{professor} cannot teach on Tuesday afternoon.',
    )
    assert {e['name'] for e in result.entities} == {professor}
    assert [r.params for r in result.rules] == [
        {'teacher': professor, 'day': 1, 'slots': [3, 4, 5]},
    ]
    assert 'Prof. Rao' not in result.model_dump_json()
    assert result.processed_files[0].file_type == 'pdf'
    assert professor in result.processed_files[0].preview


def test_unreadable_pdf_never_falls_back_to_demo_roster(isolated_intake):
    with pytest.raises(ValueError, match='PDF'):
        data_dump.ingest_data_dump(files=[('broken.pdf', b'not a PDF')])
    assert isolated_intake == []


def test_uploaded_timetable_does_not_accept_stale_demo_notes(isolated_intake):
    result = data_dump.ingest_data_dump(
        files=[('timetable.csv', b'Course,Professor\nPhysics,Dr. Marie Curie')],
        notes='Prof. Rao cannot teach Monday morning.',
    )
    assert 'Prof. Rao' not in result.model_dump_json()


def test_explicit_clock_does_not_match_another_time():
    assert data_dump._parse_days_and_slots_from_text('Dr. Lina Rivera cannot teach Tuesday at 11:00.') == (1, [2])
    assert data_dump._parse_days_and_slots_from_text('Dr. Lina Rivera cannot teach Tuesday at 12:00.') == (1, [3])


@pytest.mark.parametrize('constraint, expected', [
    ('Dr. Marie Curie is unable to teach Wednesday at 14:00.', {'teacher': 'Dr. Marie Curie', 'day': 2, 'slots': [4]}),
    ('Dr. Marie Curie should not take classes Wednesday afternoon.', {'teacher': 'Dr. Marie Curie', 'day': 2, 'slots': [3, 4, 5]}),
])
def test_common_unavailability_phrasings_are_extracted_from_uploaded_timetable(isolated_intake, constraint, expected):
    result = data_dump.ingest_data_dump(
        files=[('timetable.csv', b'Course,Professor\nPhysics,Dr. Marie Curie')],
        notes=constraint,
    )
    assert [r.params for r in result.rules if r.type == 'teacher_unavailable'] == [expected]


def test_no_rules_summary_confirms_whether_text_was_received(isolated_intake):
    result = data_dump.ingest_data_dump([], notes='Please review scheduling for next week.')
    assert 'text was received' in result.summary
    assert result.processing[0] == {'stage': 'Constraint text', 'status': 'received', 'model': 'Text input'}


def test_weekend_constraint_is_not_silently_moved_to_monday(isolated_intake):
    result = data_dump.ingest_data_dump([], notes='Prof. Rao cannot teach Saturday morning.')
    assert result.rules == []
    assert any('configured scheduling grid' in warning for warning in result.warnings)


def test_model_day_error_does_not_override_source_constraint(isolated_intake, monkeypatch):
    monkeypatch.setattr(data_dump, 'call_json', lambda **kwargs: data_dump.DataDumpLLMOut(
        summary='Incorrect day',
        rules=[data_dump.ExtractedRuleDraft(type='teacher_unavailable',
            params={'teacher': 'Prof. Rao', 'day': 1, 'slots': [0, 1, 2]})],
    ))
    result = data_dump.ingest_data_dump([], notes='Prof. Rao cannot teach Monday morning.')
    assert [rule.params['day'] for rule in result.rules] == [0]
    extraction_status = next(step['status'] for step in result.processing if step['stage'] == 'Constraint extraction')
    assert extraction_status == 'partially validated'
    assert any('discarded' in warning for warning in result.warnings)
