#!/usr/bin/env python3
"""Synthetic Multimodal Test Data Generator for GeCompose.

Generates realistic test assets across four distinct scenarios:
1. 01_university_academic: Excel workload, CSV availability, WAV dean voice memo, PNG whiteboard timetable, TXT memo.
2. 02_hospital_surgical_medops: Excel OR manifest, CSV triage cases, WAV trauma dispatch call, PNG surgical board.
3. 03_disaster_reliefops: Excel warehouse inventory, CSV camp requisitions, CSV vehicle fleet, WAV radio transmission.
4. 04_conflicts_and_edge_cases: Deliberately clashing CSV/WAV/PNG assets triggering minimal unsatisfiable cores (MUS).
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import struct
import wave

from PIL import Image, ImageDraw, ImageFont
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

BASE_DIR = Path(__file__).resolve().parent

# -----------------------------------------------------------------------------
# Audio Synthesis Utility (Synthesizes valid PCM WAV with speech-band modulation)
# -----------------------------------------------------------------------------
def synthesize_wav(
    filepath: Path,
    duration_sec: float = 4.0,
    sample_rate: int = 16000,
    base_freq: float = 220.0,
    formant_freqs: list[float] | None = None,
) -> None:
    """Generate a valid 16kHz 16-bit mono PCM WAV file with vocal-formant modulation."""
    formants = formant_freqs or [500.0, 1500.0, 2500.0]
    total_samples = int(duration_sec * sample_rate)
    samples: list[int] = []

    for i in range(total_samples):
        t = i / sample_rate
        # Vocal tract harmonic excitation with cadence envelope
        envelope = 0.5 * (1.0 + math.sin(2.0 * math.pi * 3.5 * t)) * (0.8 + 0.2 * math.sin(2.0 * math.pi * 0.5 * t))
        # Formant summation
        signal = 0.4 * math.sin(2.0 * math.pi * base_freq * t)
        for idx, f in enumerate(formants):
            weight = 0.25 / (idx + 1)
            signal += weight * math.sin(2.0 * math.pi * f * t)
        
        # Clip and scale to 16-bit integer
        val = int(max(-1.0, min(1.0, signal * envelope * 0.75)) * 32767)
        samples.append(val)

    with wave.open(str(filepath), "wb") as wf:
        wf.setnchannels(1)  # Mono
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        raw_data = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(raw_data)


# -----------------------------------------------------------------------------
# Scenario 1: University Academic Timetabling
# -----------------------------------------------------------------------------
def generate_scenario_1():
    dest = BASE_DIR / "01_university_academic"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Excel Workload Roster
    wb = openpyxl.Workbook()
    # Sheet 1: Faculty
    ws_fac = wb.active
    ws_fac.title = "Faculty_Roster"
    ws_fac.append(["Faculty ID", "Faculty Name", "Department", "Designation", "Max Weekly Hours", "Qualifications"])
    faculty_rows = [
        ["FAC-01", "Prof. Alice Vance", "Computer Science", "Professor", 16, "CS, Machine Learning, Data Science"],
        ["FAC-02", "Prof. Bob Chen", "Robotics & AI", "Associate Professor", 18, "Robotics, Control Systems, CS"],
        ["FAC-03", "Prof. Catherine Miller", "Computer Science", "Assistant Professor", 20, "Cloud Computing, Networks, CS"],
        ["FAC-04", "Dr. David Ross", "Applied Physics", "Lecturer", 14, "Quantum Computing, Physics, Math"],
        ["FAC-05", "Prof. Elena Rostova", "Information Security", "Professor", 16, "Cybersecurity, Cryptography, CS"],
    ]
    for r in faculty_rows:
        ws_fac.append(r)

    # Sheet 2: Rooms
    ws_rooms = wb.create_sheet(title="Rooms_and_Labs")
    ws_rooms.append(["Room ID", "Building", "Capacity", "Room Type", "Lab Equipment"])
    room_rows = [
        ["Auditorium A", "Turing Hall", 120, "Lecture Theatre", "Dual 4K Projectors, Surround Audio"],
        ["Room 101", "Von Neumann Block", 60, "Smart Classroom", "Interactive Smartboard, Lecture Capture"],
        ["Lab 202", "Lovelace Centre", 35, "Computer Lab", "35 High-Performance GPU Workstations"],
        ["Seminar 303", "Shannon Hall", 25, "Discussion Room", "Video Conferencing, Whiteboards"],
    ]
    for r in room_rows:
        ws_rooms.append(r)

    # Sheet 3: Courses
    ws_courses = wb.create_sheet(title="Courses_and_Workload")
    ws_courses.append(["Course Code", "Course Title", "Primary Instructor", "Expected Students", "Weekly Slots", "Required Room"])
    course_rows = [
        ["CS501", "Advanced Machine Learning", "Prof. Alice Vance", 55, 3, "Room 101"],
        ["CS502", "Robotics Systems Lab", "Prof. Bob Chen", 30, 2, "Lab 202"],
        ["CS503", "Cloud Architecture", "Prof. Catherine Miller", 50, 3, "Room 101"],
        ["CS504", "Quantum Computing Seminar", "Dr. David Ross", 20, 2, "Seminar 303"],
        ["CS505", "Cybersecurity Operations", "Prof. Elena Rostova", 45, 3, "Room 101"],
    ]
    for r in course_rows:
        ws_courses.append(r)

    # Styling Excel headers
    header_fill = PatternFill(start_color="1F2937", end_color="1F2937", fill_type="solid")
    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    for ws in [ws_fac, ws_rooms, ws_courses]:
        for cell in ws[1]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    wb.save(dest / "faculty_workload_roster.xlsx")

    # 2. CSV Availability
    csv_content = """Faculty,Day,Slots_Unavailable,Reason
Prof. Alice Vance,Monday,"0,1",Dean's Executive Committee
Prof. Bob Chen,Thursday,"3,4",Robotics Lab Calibration & Servicing
Prof. Elena Rostova,Friday,"4,5",Cyber Defense Industry Advisory Board
"""
    (dest / "faculty_availability.csv").write_text(csv_content, encoding="utf-8")

    # 3. Audio Voice Memo (Dean dictating constraints)
    synthesize_wav(
        dest / "dean_voice_memo.wav",
        duration_sec=5.0,
        base_freq=180.0,
        formant_freqs=[600.0, 1600.0, 2400.0],
    )

    # 4. Whiteboard Weekly Timetable PNG Image
    img = Image.new("RGB", (1200, 800), color=(15, 23, 42))  # Slate dark
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    # Title Banner
    draw.rectangle([(20, 20), (1180, 70)], fill=(30, 41, 59), outline=(71, 85, 105))
    draw.text((40, 35), "DEPARTMENT OF COMPUTER SCIENCE - WEEKLY SCHEDULE MATRIX (SEMESTER 1)", fill=(248, 250, 252), font=font)

    # Table Grid
    days = ["Time", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    col_w = 190
    row_h = 95
    start_x, start_y = 30, 90

    # Header Row
    for idx, d in enumerate(days):
        x = start_x + idx * col_w
        draw.rectangle([(x, start_y), (x + col_w, start_y + 40)], fill=(51, 65, 85), outline=(100, 116, 139))
        draw.text((x + 20, start_y + 12), d, fill=(241, 245, 249), font=font)

    # Times & Cells
    times = ["09:00 - 10:00", "10:00 - 11:00", "11:00 - 12:00", "12:00 - 13:00", "14:00 - 15:00", "15:00 - 16:00"]
    for row_idx, t in enumerate(times):
        y = start_y + 40 + row_idx * row_h
        # Time Label
        draw.rectangle([(start_x, y), (start_x + col_w, y + row_h)], fill=(30, 41, 59), outline=(71, 85, 105))
        draw.text((start_x + 15, y + 35), t, fill=(148, 163, 184), font=font)
        # Day Cells
        for col_idx in range(1, 6):
            x = start_x + col_idx * col_w
            draw.rectangle([(x, y), (x + col_w, y + row_h)], fill=(15, 23, 42), outline=(51, 65, 85))

    # Add Course Cards
    # Wed Slot 1 (10:00 - 11:00): CS501 Pinned
    cs501_x = start_x + 3 * col_w + 5
    cs501_y = start_y + 40 + 1 * row_h + 5
    draw.rectangle([(cs501_x, cs501_y), (cs501_x + col_w - 10, cs501_y + row_h - 10)], fill=(30, 58, 138), outline=(96, 165, 250))
    draw.text((cs501_x + 10, cs501_y + 12), "CS501: Machine Learning", fill=(255, 255, 255), font=font)
    draw.text((cs501_x + 10, cs501_y + 35), "Prof. Alice Vance", fill=(191, 219, 254), font=font)
    draw.text((cs501_x + 10, cs501_y + 55), "Room 101 [PINNED]", fill=(253, 224, 71), font=font)

    # Tue Slot 0 (09:00 - 10:00): Lab 202 Offline
    lab_x = start_x + 2 * col_w + 5
    lab_y = start_y + 40 + 0 * row_h + 5
    draw.rectangle([(lab_x, lab_y), (lab_x + col_w - 10, lab_y + row_h - 10)], fill=(127, 29, 29), outline=(239, 68, 68))
    draw.text((lab_x + 10, lab_y + 15), "MAINTENANCE OFFLINE", fill=(254, 202, 202), font=font)
    draw.text((lab_x + 10, lab_y + 40), "Lab 202 Hardware Check", fill=(255, 255, 255), font=font)

    # Sticky Note Annotation
    draw.rectangle([(930, 680), (1170, 770)], fill=(254, 240, 138), outline=(202, 138, 4))
    draw.text((945, 695), "* NOTE: Alice Vance", fill=(113, 63, 18), font=font)
    draw.text((945, 715), "  unavailable Mon AM", fill=(113, 63, 18), font=font)
    draw.text((945, 735), "* CS502 lab restricted to Bob", fill=(113, 63, 18), font=font)

    img.save(dest / "whiteboard_weekly_schedule.png")

    # 5. Departmental Memo
    memo_txt = """MEMORANDUM: Academic Scheduling Directorate
TO: Timetable Coordinating Committee
FROM: Prof. M. Henderson, Dean of Computer Science
DATE: 2026-10-10
SUBJECT: Term 1 Scheduling Invariants & Section Placement Rules

Please incorporate the following mandatory operational constraints into the solver:
1. Faculty Unavailability:
   - Prof. Alice Vance cannot take classes on Monday morning (Slots 0 and 1) due to University Senate duties.
   - Prof. Bob Chen is conducting robotics calibrations on Thursday afternoon (Slots 3 and 4).
2. Lab Equipment Constraints:
   - Lab 202 is undergoing hardware diagnostics on Tuesday Slot 0 (09:00 - 10:00). No sessions may be placed in Lab 202 during that time.
3. Locked / Pinned Classrooms:
   - CS501 (Advanced Machine Learning) is locked to Wednesday Slot 1 (10:00 - 11:00) in Room 101.
4. Instructor Qualifications:
   - CS502 (Robotics Systems Lab) must only be assigned to Prof. Bob Chen.
"""
    (dest / "departmental_memo.txt").write_text(memo_txt, encoding="utf-8")

    # 6. Expected Ground Truth Schema
    expected_rules = {
        "scenario": "university_academic_term1",
        "expected_faculty": ["Prof. Alice Vance", "Prof. Bob Chen", "Prof. Catherine Miller", "Dr. David Ross", "Prof. Elena Rostova"],
        "expected_rooms": ["Auditorium A", "Room 101", "Lab 202", "Seminar 303"],
        "expected_rules": [
            {"type": "teacher_unavailable", "params": {"teacher": "Prof. Alice Vance", "day": 0, "slots": [0, 1]}},
            {"type": "teacher_unavailable", "params": {"teacher": "Prof. Bob Chen", "day": 3, "slots": [3, 4]}},
            {"type": "room_unavailable", "params": {"room": "Lab 202", "day": 1, "slots": [0]}},
            {"type": "pin_session", "params": {"session_id": "CS501", "day": 2, "slots": [1]}},
            {"type": "only_qualified", "params": {"session_id": "CS502", "teachers": ["Prof. Bob Chen"]}}
        ]
    }
    (dest / "expected_rules.json").write_text(json.dumps(expected_rules, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Scenario 2: Hospital Emergency Surgical Suites (MedOps)
# -----------------------------------------------------------------------------
def generate_scenario_2():
    dest = BASE_DIR / "02_hospital_surgical_medops"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Excel OR Manifest
    wb = openpyxl.Workbook()
    ws_cases = wb.active
    ws_cases.title = "Surgical_Cases"
    ws_cases.append(["Case ID", "Patient MRN", "Patient Name", "Specialty", "Triage Urgency", "Duration (Min)", "Lead Surgeon", "Anesthesiologist"])
    cases = [
        ["CASE-TR-01", "MRN-9011", "Trauma Patient Alpha", "Trauma", "RESUSCITATION_L1", 120, "Dr. Sarah Connor", "Dr. Marcus Brody"],
        ["CASE-CARD-02", "MRN-9012", "Emergency Aneurysm", "Cardiac", "RESUSCITATION_L1", 180, "Dr. Victor Vance", "Dr. Marcus Brody"],
        ["CASE-GEN-03", "MRN-9013", "Acute Appendectomy", "General Surgery", "URGENT_L2", 60, "Dr. Emily Hayes", "Dr. Nina Patel"],
        ["CASE-ORTHO-04", "MRN-9014", "Femur Open Reduction", "Orthopedics", "URGENT_L2", 90, "Dr. James Wilson", "Dr. Nina Patel"],
        ["CASE-ELEC-05", "MRN-9015", "Elective Cholecystectomy", "General Surgery", "ELECTIVE_L3", 75, "Dr. Emily Hayes", "Dr. Marcus Brody"],
    ]
    for c in cases:
        ws_cases.append(c)

    ws_theatres = wb.create_sheet(title="Operating_Theatres")
    ws_theatres.append(["OR Suite ID", "Name", "Specialty Capability", "Sterilization Buffer (Min)", "Operating Window"])
    theatres = [
        ["OR-TRAUMA-1", "Level-1 Trauma Surgical Suite", "Trauma, Vascular", 25, "00:00 - 24:00"],
        ["OR-CARDIAC-2", "Hybrid Cardiac Operating Suite", "Cardiac, Vascular", 30, "07:00 - 22:00"],
        ["OR-GENERAL-3", "General Surgical Suite A", "General Surgery, Ortho", 20, "08:00 - 20:00"],
    ]
    for t in theatres:
        ws_theatres.append(t)

    wb.save(dest / "or_surgical_manifest.xlsx")

    # 2. CSV Triage Cases
    csv_cases = """Case_ID,Patient_MRN,Specialty,Urgency_Tier,Duration_Minutes,Lead_Surgeon_Required
CASE-TR-01,MRN-9011,Trauma,L1_EMERGENT,120,Dr. Sarah Connor
CASE-CARD-02,MRN-9012,Cardiac,L1_EMERGENT,180,Dr. Victor Vance
CASE-GEN-03,MRN-9013,General,L2_URGENT,60,Dr. Emily Hayes
CASE-ORTHO-04,MRN-9014,Orthopedics,L2_URGENT,90,Dr. James Wilson
CASE-ELEC-05,MRN-9015,General,L3_ELECTIVE,75,Dr. Emily Hayes
"""
    (dest / "triage_cases.csv").write_text(csv_cases, encoding="utf-8")

    # 3. Audio Emergency Dispatch Call
    synthesize_wav(
        dest / "trauma_dispatch_call.wav",
        duration_sec=4.5,
        base_freq=240.0,
        formant_freqs=[800.0, 1800.0, 2800.0],
    )

    # 4. Surgical Whiteboard PNG
    img = Image.new("RGB", (1200, 800), color=(10, 15, 29))  # Deep clinical navy
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.rectangle([(20, 20), (1180, 70)], fill=(23, 37, 84), outline=(59, 130, 246))
    draw.text((40, 35), "TRAUMA CENTRE OPERATING THEATRE BOARD - ACTIVE CASE ROTATION", fill=(255, 255, 255), font=font)

    # Columns: OR-1, OR-2, OR-3
    suites = ["OR-1 (Level 1 Trauma)", "OR-2 (Hybrid Cardiac)", "OR-3 (General & Ortho)"]
    for i, s in enumerate(suites):
        x = 50 + i * 380
        draw.rectangle([(x, 90), (x + 350, 750)], fill=(15, 23, 42), outline=(71, 85, 105))
        draw.rectangle([(x, 90), (x + 350, 140)], fill=(30, 41, 59), outline=(100, 116, 139))
        draw.text((x + 20, 105), s, fill=(248, 250, 252), font=font)

        # Cases in Suite
        if i == 0:
            # Emergent Trauma Card
            draw.rectangle([(x + 15, 160), (x + 335, 280)], fill=(127, 29, 29), outline=(239, 68, 68))
            draw.text((x + 25, 175), "[L1 RESUSCITATION] CASE-TR-01", fill=(255, 255, 255), font=font)
            draw.text((x + 25, 200), "Trauma Laparotomy - 120 min", fill=(254, 202, 202), font=font)
            draw.text((x + 25, 225), "Surgeon: Dr. Sarah Connor", fill=(255, 255, 255), font=font)
            draw.text((x + 25, 250), "Buffer: 25 min Sterilization Required", fill=(253, 224, 71), font=font)
        elif i == 1:
            # Cardiac Case
            draw.rectangle([(x + 15, 160), (x + 335, 280)], fill=(136, 19, 55), outline=(244, 63, 94))
            draw.text((x + 25, 175), "[L1 CRITICAL] CASE-CARD-02", fill=(255, 255, 255), font=font)
            draw.text((x + 25, 200), "Aneurysm Repair - 180 min", fill=(254, 205, 211), font=font)
            draw.text((x + 25, 225), "Surgeon: Dr. Victor Vance", fill=(255, 255, 255), font=font)
        elif i == 2:
            # Elective Case
            draw.rectangle([(x + 15, 160), (x + 335, 280)], fill=(30, 58, 138), outline=(59, 130, 246))
            draw.text((x + 25, 175), "[L2 URGENT] CASE-GEN-03", fill=(255, 255, 255), font=font)
            draw.text((x + 25, 200), "Appendectomy - 60 min", fill=(191, 219, 254), font=font)
            draw.text((x + 25, 225), "Surgeon: Dr. Emily Hayes", fill=(255, 255, 255), font=font)

    img.save(dest / "surgical_board_whiteboard.png")

    # 5. Expected Plan Schema
    expected_plan = {
        "scenario": "hospital_surgical_trauma_intake",
        "benchmark": "Level-1 Trauma Center Benchmarking",
        "total_operating_rooms": 3,
        "expected_scheduled_cases": 5,
        "max_turnaround_sterilization_minutes": 30,
        "preemption_policy": "L1_EMERGENT preempts L3_ELECTIVE strictly"
    }
    (dest / "expected_plan.json").write_text(json.dumps(expected_plan, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Scenario 3: Disaster ReliefOps Supply Chain Logistics
# -----------------------------------------------------------------------------
def generate_scenario_3():
    dest = BASE_DIR / "03_disaster_reliefops"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Excel Inventory
    wb = openpyxl.Workbook()
    ws_depots = wb.active
    ws_depots.title = "Warehouses"
    ws_depots.append(["Depot ID", "Facility Name", "District", "Operational Status", "Available Capacity M3"])
    ws_depots.append(["DEPOT-CENTRAL", "Regional Logistics Hub", "Central District", "OPERATIONAL", 1500])
    ws_depots.append(["DEPOT-NORTH", "Northern Forward Depot", "Highland District", "LIMITED_ACCESS", 600])

    ws_stock = wb.create_sheet(title="Inventory_Stock")
    ws_stock.append(["Item ID", "Category", "Quantity Available", "Unit Weight (KG)", "Unit Volume (M3)"])
    items = [
        ["WATER_LITERS", "POTABLE_WATER", 35000, 1.0, 0.001],
        ["MEDICAL_KITS", "MEDICAL_SUPPLIES", 850, 4.5, 0.02],
        ["EMERGENCY_RATIONS", "FOOD_RATIONS", 15000, 0.75, 0.002],
        ["SHELTER_TENTS", "TEMPORARY_SHELTER", 1200, 18.0, 0.15],
    ]
    for it in items:
        ws_stock.append(it)

    wb.save(dest / "regional_depot_inventory.xlsx")

    # 2. CSV Camp Requisition
    csv_camps = """Camp_ID,Camp_Name,Population,Urgency_Level,Water_Requested,Rations_Requested,Medical_Kits_Requested
CAMP-RIVER-A,Camp River Alpha (Flood Zone),1400,CRITICAL_L1,8000,3000,120
CAMP-HILL-B,Camp Hill Beta (Highlands),950,HIGH_L2,5000,2000,60
CAMP-VALLEY-C,Camp Valley Gamma (Evac Center),620,MODERATE_L3,3500,1200,35
"""
    (dest / "relief_camps_requisition.csv").write_text(csv_camps, encoding="utf-8")

    # 3. CSV Vehicle Fleet Manifest
    csv_fleet = """Vehicle_ID,Vehicle_Type,Payload_Capacity_KG,Max_Volume_M3,Status,Range_KM
TRUCK-HEAVY-01,10-Ton Heavy Cargo Truck,10000,35.0,READY,450
TRUCK-MEDIUM-02,5-Ton All-Terrain Truck,5000,20.0,READY,350
HELI-CARGO-03,Emergency Cargo Helicopter,2500,12.0,READY,200
"""
    (dest / "vehicle_fleet_manifest.csv").write_text(csv_fleet, encoding="utf-8")

    # 4. Audio Radio Transmission
    synthesize_wav(
        dest / "field_radio_transmission.wav",
        duration_sec=4.0,
        base_freq=300.0,
        formant_freqs=[900.0, 2100.0, 3100.0],
    )

    # 5. Expected Allocation Schema
    expected_alloc = {
        "scenario": "cyclone_disaster_phase1",
        "total_camps": 3,
        "critical_priority_camp": "CAMP-RIVER-A",
        "expected_fulfillment_rate_target": 0.85,
        "objective": "Maximin equitable distribution weighted by urgency tier"
    }
    (dest / "expected_allocation.json").write_text(json.dumps(expected_alloc, indent=2), encoding="utf-8")


# -----------------------------------------------------------------------------
# Scenario 4: Conflicts & Edge Cases (Deliberate MUS Core)
# -----------------------------------------------------------------------------
def generate_scenario_4():
    dest = BASE_DIR / "04_conflicts_and_edge_cases"
    dest.mkdir(parents=True, exist_ok=True)

    # 1. Deliberate Infeasible CSV Matrix (2 classes pinned to same room & time)
    csv_conflict = """Session_ID,Course_Title,Assigned_Teacher,Pinned_Day,Pinned_Slot,Pinned_Room
DATA_STRUCT,Data Structures & Algorithms,Prof. Turing,0,0,Room 101
OPERATING_SYS,Operating Systems Principles,Prof. Turing,0,0,Room 101
"""
    (dest / "impossible_pinned_overlap.csv").write_text(csv_conflict, encoding="utf-8")

    # 2. Audio Voicemail with Clashing Availability
    synthesize_wav(
        dest / "faculty_clash_voicemail.wav",
        duration_sec=3.5,
        base_freq=160.0,
        formant_freqs=[500.0, 1400.0, 2200.0],
    )

    # 3. Conflict Notice Photo PNG
    img = Image.new("RGB", (1000, 600), color=(24, 24, 27))
    draw = ImageDraw.Draw(img)
    font = ImageFont.load_default()

    draw.rectangle([(20, 20), (980, 580)], fill=(9, 9, 11), outline=(239, 68, 68), width=3)
    draw.rectangle([(40, 40), (960, 90)], fill=(127, 29, 29))
    draw.text((60, 55), "CRITICAL SCHEDULING CONFLICT DETECTED - UNSATISFIABLE CORE", fill=(255, 255, 255), font=font)

    # Conflict details
    draw.text((60, 120), "Collision 1: Session 'DATA_STRUCT' and 'OPERATING_SYS' both pinned to:", fill=(254, 202, 202), font=font)
    draw.text((100, 150), "* Day 0 (Monday) Slot 0 (09:00 - 10:00)", fill=(255, 255, 255), font=font)
    draw.text((100, 175), "* Room: Room 101 (Double Room Overlap)", fill=(255, 255, 255), font=font)
    draw.text((100, 200), "* Instructor: Prof. Turing (Teacher Double-Booking)", fill=(255, 255, 255), font=font)

    # Resolution Box
    draw.rectangle([(60, 250), (940, 420)], fill=(24, 24, 27), outline=(234, 179, 8))
    draw.text((80, 270), "Gemma 12B Recommended Relaxation Candidates:", fill=(253, 224, 71), font=font)
    draw.text((80, 310), "Option 1: Shift 'OPERATING_SYS' to Monday Slot 1 (10:00 - 11:00) in Room 101", fill=(244, 244, 245), font=font)
    draw.text((80, 340), "Option 2: Reassign 'OPERATING_SYS' to qualified instructor Prof. Lovelace in Room 102", fill=(244, 244, 245), font=font)

    img.save(dest / "conflict_notice_photo.png")

    # 4. Expected MUS Core JSON
    expected_mus = {
        "status": "infeasible",
        "is_minimal": True,
        "conflicting_rule_types": ["pin_session", "teacher_non_overlap", "room_non_overlap"],
        "conflicting_sessions": ["DATA_STRUCT", "OPERATING_SYS"],
        "recommended_relaxations": [
            {"candidate": "move_slot", "target": "OPERATING_SYS", "new_slot": 1},
            {"candidate": "swap_room_or_teacher", "target": "OPERATING_SYS", "new_teacher": "Prof. Lovelace"}
        ]
    }
    (dest / "expected_mus_core.json").write_text(json.dumps(expected_mus, indent=2), encoding="utf-8")


def main():
    print("Generating synthetic multimodal test datasets in test_data/...")
    generate_scenario_1()
    print("  ✓ Scenario 1: University Academic Timetabling generated.")
    generate_scenario_2()
    print("  ✓ Scenario 2: Hospital Surgical MedOps generated.")
    generate_scenario_3()
    print("  ✓ Scenario 3: Disaster ReliefOps Supply Chain generated.")
    generate_scenario_4()
    print("  ✓ Scenario 4: Conflicts & MUS Edge Cases generated.")
    print("All multimodal synthetic test data successfully generated!")


if __name__ == "__main__":
    main()
