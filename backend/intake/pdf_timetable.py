"""Read aligned PDF timetable text without asking a model to guess cell times."""
from __future__ import annotations

import re
from typing import Literal
from pydantic import BaseModel, model_validator

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
CODE = re.compile(r'(?<![A-Z0-9_-])[A-Z0-9]{6,}(?![A-Z0-9_-])')
TIME = re.compile(r'(\d{1,2}):([0-5]\d)\s*[-–]\s*(\d{1,2}):([0-5]\d)')
TITLE = re.compile(r'\b(?:Prof(?:essor)?\.?|Dr\.?)\s+(?:[A-Z]\.?[ \t]*)*[A-Z][a-z][A-Za-z’\'-]*(?:[ \t]+[A-Z][a-z][A-Za-z’\'-]*){0,3}')


class PDFClass(BaseModel):
    day: Literal['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    start: str
    end: str
    course_code: str
    teachers: list[str]
    room: str

    @model_validator(mode='after')
    def valid_window(self):
        if any(not re.fullmatch(r'([01][0-9]|2[0-3]):[0-5][0-9]', value) for value in (self.start, self.end)):
            raise ValueError('Times must use HH:MM')
        if self.start >= self.end:
            raise ValueError('Class end must be later than start')
        return self


class PDFTimetable(BaseModel):
    classes: list[PDFClass]
    warnings: list[str]


def _codes(line):
    return [m for m in CODE.finditer(line) if any(c.isdigit() for c in m.group()) and any(c.isalpha() for c in m.group())]


def _legend(lines: list[str], faculty: list[str]):
    header = next((i for i, line in enumerate(lines) if re.search(r'Course\s+Code.*Coordinator', line, re.I)), None)
    if header is None:
        return {}, {}
    starts = [m.start() for m in re.finditer(r'Course\s+Code', lines[header], re.I)]
    boundaries = [0] + [max(0, start - 10) for start in starts[1:]] + [max(map(len, lines)) + 1]
    assignments, aliases = {}, {}
    for left, right in zip(boundaries, boundaries[1:]):
        section = [line[left:right] for line in lines[header + 1:]]
        course_rows = [(i, m.group(), m.end()) for i, line in enumerate(section) for m in _codes(line)]
        if not course_rows:
            continue
        groups = {code: [] for _, code, _ in course_rows}
        for i, line in enumerate(section):
            nearest = min(course_rows, key=lambda entry: abs(entry[0] - i))
            groups[nearest[1]].append(line)
        for _, code, code_end in course_rows:
            block = groups[code]
            teachers = []
            teacher_starts = [m.start() for line in block for m in TITLE.finditer(line)]
            title_end = min(teacher_starts) if teacher_starts else max(map(len, block), default=code_end)
            title = ' '.join(re.split(r'\bB[0-9]|\*\*', line[code_end:title_end])[0].strip() for line in block).strip()
            for line in block:
                for match in TITLE.finditer(line):
                    name = re.sub(r'\s+', ' ', match.group()).strip()
                    if name in faculty:
                        teachers.append(name)
            assignments[code] = list(dict.fromkeys(teachers))
            for acronym in re.findall(r'\(([A-Z ]+)\)', title):
                aliases[acronym.replace(' ', '')] = code
            words = re.findall(r'[A-Za-z]+', re.sub(r'\([^)]*\)', '', title))
            words = [word for word in words if word.lower() not in {'and', 'for', 'the', 'lab'}]
            if words:
                aliases[''.join(word[0].upper() for word in words)] = code
    return assignments, aliases


def extract_pdf_timetable(text: str, faculty: list[str]) -> PDFTimetable:
    lines = text.splitlines()
    header = next((i for i, line in enumerate(lines) if len(list(TIME.finditer(line))) >= 2), None)
    if header is None:
        return PDFTimetable(classes=[], warnings=['No aligned time header found; PDF class placements could not be read.'])
    windows = []
    previous = -1
    for match in TIME.finditer(lines[header]):
        hour, minute, end_hour, end_minute = map(int, match.groups())
        start = hour * 60 + minute
        while start < previous and hour < 12:
            start += 12 * 60
            hour += 12
        end = end_hour * 60 + end_minute
        while end <= start:
            end += 12 * 60
        previous = start
        windows.append(((match.start() + match.end()) / 2, f'{start // 60:02d}:{start % 60:02d}', f'{end // 60:02d}:{end % 60:02d}'))
    days = [(i, match.group(1).title()) for i, line in enumerate(lines[header + 1:], header + 1)
            if (match := re.match(r'^\s*(MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\b', line, re.I))]
    if not days:
        return PDFTimetable(classes=[], warnings=['No aligned weekday rows found; PDF class placements could not be read.'])
    teachers_by_code, aliases = _legend(lines, faculty)
    default_room = re.search(r'Room\s*(?:No)?\s*[:.]\s*([A-Z]+\s*\d+)', text, re.I)
    room = re.sub(r'\s+', '', default_room.group(1)) if default_room else ''
    classes, warnings, seen = [], [], set()
    for line_index in range(header + 1, min(len(lines), days[-1][0] + 2)):
        line = lines[line_index]
        day_index, day = min(days, key=lambda entry: abs(entry[0] - line_index))
        # Wrapped cells occupy the lines adjacent to a row's weekday label.
        if abs(day_index - line_index) > 1:
            continue
        for chunk in re.finditer(r'\S(?:.*?\S)?(?= {2,}|$)', line):
            value = chunk.group()
            matches = _codes(value)
            code = matches[0].group() if matches else ''
            if not code and 'lab' in value.lower():
                prefix = re.split(r'\s+lab\b', value, flags=re.I)[0].replace(' ', '').upper()
                code = aliases.get(prefix, '')
            if not code:
                if chunk.start() > 15 and value not in {'RECESS', 'OE'} and not re.search(r'\b(?:MONDAY|TUESDAY|WEDNESDAY|THURSDAY|FRIDAY|SATURDAY|SUNDAY)\b', value, re.I) and not re.search(r'\b(?:NGD|DP)-', value):
                    warnings.append(f'{day}: cell "{value}" has no identified course code and was not imported.')
                continue
            indices = [i for i, (center, _, _) in enumerate(windows) if chunk.start() - 4 <= center <= chunk.end() + 4]
            if 'lab' not in value.lower() or not indices:
                center = chunk.start() + (matches[0].start() + matches[0].end()) / 2 if matches else (chunk.start() + chunk.end()) / 2
                indices = [min(range(len(windows)), key=lambda i: abs(windows[i][0] - center))]
            # Labs spanning a merged cell cover the time-header centers inside that cell.
            assigned = teachers_by_code.get(code, [])
            if not assigned:
                warnings.append(f'{code}: no matching faculty assignment in the PDF legend; instructor remains unknown.')
            rooms = re.findall(r'\b[A-Z]{1,5}\s*\d{3}\b', value)
            selected_rooms = [re.sub(r'\s+', '', r) for r in rooms] or [room]
            for selected_room in selected_rooms:
                placement = PDFClass(day=day, start=windows[min(indices)][1], end=windows[max(indices)][2], course_code=code, teachers=assigned, room=selected_room)
                key = (day, placement.start, placement.end, code, selected_room)
                if key not in seen:
                    seen.add(key)
                    classes.append(placement)
    if any('lab' in line.lower() and re.search(r'B\d', line) for line in lines):
        warnings.append('Batch-specific labs list candidate instructors from the course legend; review batch assignments before applying changes.')
    return PDFTimetable(classes=classes, warnings=list(dict.fromkeys(warnings)))


def overlaps_rule(placement: PDFClass, rule_type: str, params: dict, slot_times: list[str]) -> bool:
    if rule_type not in {'teacher_unavailable', 'room_unavailable'}:
        return False
    if WEEKDAYS.index(placement.day) != params['day']:
        return False
    if rule_type == 'teacher_unavailable' and params['teacher'] not in placement.teachers:
        return False
    if rule_type == 'room_unavailable' and params['room'] != placement.room:
        return False
    def minutes(value):
        hours, minute = map(int, value.split(':'))
        return hours * 60 + minute
    start, end = minutes(placement.start), minutes(placement.end)
    return any(start < minutes(slot_times[slot]) + 60 and end > minutes(slot_times[slot]) for slot in params['slots'])
