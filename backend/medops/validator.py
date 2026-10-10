"""Independent clinical and physical constraint validator for hospital surgical theatre schedules."""
from __future__ import annotations

from backend.medops.models import (
    HospitalORPlan,
    MedicalStaff,
    OperatingRoom,
    PatientCase,
    SurgicalSpecialty,
)


class HospitalValidationError(ValueError):
    """Raised when an operating theatre schedule violates clinical safety invariants."""
    pass


def validate_hospital_plan(
    plan: HospitalORPlan,
    operating_rooms: list[OperatingRoom],
    staff: list[MedicalStaff],
    patient_cases: list[PatientCase],
    icu_bed_capacity: int = 8,
) -> tuple[bool, list[str]]:
    """Strictly verify clinical safety, sterility intervals, and non-overlap invariants independently."""
    violations: list[str] = []

    room_map = {r.id: r for r in operating_rooms}
    staff_map = {s.id: s for s in staff}
    case_map = {c.id: c for c in patient_cases}

    items = plan.items

    # 1. Verify Operating Room Non-Overlap and Turnaround Sterilization
    room_schedules: dict[str, list] = {r.id: [] for r in operating_rooms}
    for item in items:
        room_schedules[item.or_room_id].append(item)

    for r_id, scheduled in room_schedules.items():
        room = room_map.get(r_id)
        if not room:
            violations.append(f"Unknown Operating Room ID in schedule: '{r_id}'")
            continue
        if not room.is_operational and scheduled:
            violations.append(f"Operating Room '{room.name}' is OFFLINE but has {len(scheduled)} surgeries assigned!")

        # Sort by start minute
        sorted_items = sorted(scheduled, key=lambda x: x.start_minute)
        for i in range(len(sorted_items) - 1):
            curr = sorted_items[i]
            nxt = sorted_items[i + 1]

            required_clearance = curr.end_minute + room.turnaround_sterilization_minutes
            if nxt.start_minute < curr.end_minute:
                violations.append(
                    f"CRITICAL DOUBLE-BOOKING in {room.name}: Case '{curr.case_id}' ({curr.start_minute}-{curr.end_minute}m) "
                    f"overlaps with Case '{nxt.case_id}' ({nxt.start_minute}-{nxt.end_minute}m)"
                )
            elif nxt.start_minute < required_clearance:
                violations.append(
                    f"STERILITY VIOLATION in {room.name}: Case '{nxt.case_id}' starts at {nxt.start_minute}m before "
                    f"turnaround sterilization window ends ({required_clearance}m) for Case '{curr.case_id}'"
                )

    # 2. Verify Lead Surgeon Non-Overlap
    surg_schedules: dict[str, list] = {}
    for item in items:
        surg_schedules.setdefault(item.lead_surgeon_id, []).append(item)

    for surg_id, scheduled in surg_schedules.items():
        surg = staff_map.get(surg_id)
        sorted_s = sorted(scheduled, key=lambda x: x.start_minute)
        for i in range(len(sorted_s) - 1):
            curr = sorted_s[i]
            nxt = sorted_s[i + 1]
            if nxt.start_minute < curr.end_minute:
                violations.append(
                    f"CLINICAL STAFF OVERLAP: Lead Surgeon '{surg.name if surg else surg_id}' double-booked across "
                    f"cases '{curr.case_id}' ({curr.or_room_name}) and '{nxt.case_id}' ({nxt.or_room_name})!"
                )

    # 3. Verify Anesthesiologist Non-Overlap
    anes_schedules: dict[str, list] = {}
    for item in items:
        anes_schedules.setdefault(item.anesthesiologist_id, []).append(item)

    for anes_id, scheduled in anes_schedules.items():
        anes = staff_map.get(anes_id)
        sorted_a = sorted(scheduled, key=lambda x: x.start_minute)
        for i in range(len(sorted_a) - 1):
            curr = sorted_a[i]
            nxt = sorted_a[i + 1]
            if nxt.start_minute < curr.end_minute:
                violations.append(
                    f"ANESTHESIOLOGIST OVERLAP: '{anes.name if anes else anes_id}' double-booked across "
                    f"cases '{curr.case_id}' and '{nxt.case_id}'!"
                )

    # 4. Verify Earliest Arrival and Equipment Matching
    for item in items:
        case = case_map.get(item.case_id)
        if not case:
            violations.append(f"Scheduled Case ID '{item.case_id}' not found in registry")
            continue

        if item.start_minute < case.arrival_minute:
            violations.append(
                f"TIME PARADOX: Patient '{case.patient_name}' scheduled at {item.start_minute}m before arrival ({case.arrival_minute}m)"
            )

        # Check required equipment in assigned room
        room = room_map.get(item.or_room_id)
        if room:
            missing_equip = [eq for eq in case.required_equipment if eq not in room.equipped_capabilities]
            if missing_equip:
                violations.append(
                    f"EQUIPMENT MISMATCH: Case '{case.id}' in {room.name} lacks required equipment: {', '.join(missing_equip)}"
                )

        # Check surgeon specialty
        surg = staff_map.get(item.lead_surgeon_id)
        if surg and surg.specialties:
            if case.specialty not in surg.specialties and SurgicalSpecialty.GENERAL_SURGERY not in surg.specialties:
                violations.append(
                    f"CREDENTIAL MISMATCH: Surgeon '{surg.name}' ({[s.value for s in surg.specialties]}) not credentialed for {case.specialty.value}"
                )

    is_valid = len(violations) == 0
    return is_valid, violations
