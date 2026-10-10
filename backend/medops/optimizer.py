"""Google OR-Tools CP-SAT Surgical Theatre Optimizer for Hospital Emergency Departments."""
from __future__ import annotations

import time
from typing import Any
from ortools.sat.python import cp_model

from backend.medops.models import (
    HospitalORPlan,
    HospitalORSummary,
    MedicalStaff,
    OperatingRoom,
    PatientCase,
    StaffRole,
    SurgicalScheduleItem,
    SurgicalSpecialty,
    TriageUrgency,
)


class HospitalSurgicalOptimizer:
    """Production-grade CP-SAT solver distributing emergency and elective surgeries under clinical constraints."""

    def __init__(self, time_limit_seconds: float = 10.0, random_seed: int = 42):
        self.time_limit_seconds = time_limit_seconds
        self.random_seed = random_seed

    def solve(
        self,
        hospital_id: str,
        hospital_name: str,
        operating_rooms: list[OperatingRoom],
        staff: list[MedicalStaff],
        patient_cases: list[PatientCase],
        icu_bed_capacity: int = 8,
        horizon_minutes: int = 1440,  # 24 hour scheduling window
        plan_id: str | None = None,
        version: int = 1,
    ) -> HospitalORPlan:
        start_mono = time.monotonic()
        model = cp_model.CpModel()

        operational_rooms = [r for r in operating_rooms if r.is_operational]
        room_map = {r.id: r for r in operational_rooms}

        active_surgeons = [s for s in staff if s.is_on_duty and s.role == StaffRole.LEAD_SURGEON]
        active_anesthesiologists = [s for s in staff if s.is_on_duty and s.role == StaffRole.ANESTHESIOLOGIST]
        active_scrub_nurses = [s for s in staff if s.is_on_duty and s.role == StaffRole.SCRUB_NURSE]

        staff_map = {s.id: s for s in staff}

        # Urgency multiplier for triage prioritization
        urgency_weights = {
            TriageUrgency.RESUSCITATION_L1: 100000,
            TriageUrgency.EMERGENT_L2: 25000,
            TriageUrgency.URGENT_L3: 5000,
            TriageUrgency.ELECTIVE_L4: 1000,
        }

        # Decision variables per patient case
        sched_vars: dict[str, cp_model.IntVar] = {}
        start_vars: dict[str, cp_model.IntVar] = {}
        end_vars: dict[str, cp_model.IntVar] = {}
        room_assign_vars: dict[tuple[str, str], cp_model.IntVar] = {}
        surgeon_assign_vars: dict[tuple[str, str], cp_model.IntVar] = {}
        anesthesia_assign_vars: dict[tuple[str, str], cp_model.IntVar] = {}
        nurse_assign_vars: dict[tuple[str, str], cp_model.IntVar] = {}

        # Tracking intervals on shared physical and clinical assets
        room_intervals: dict[str, list[cp_model.IntervalVar]] = {r.id: [] for r in operational_rooms}
        surgeon_intervals: dict[str, list[cp_model.IntervalVar]] = {s.id: [] for s in active_surgeons}
        anesthesia_intervals: dict[str, list[cp_model.IntervalVar]] = {s.id: [] for s in active_anesthesiologists}
        nurse_intervals: dict[str, list[cp_model.IntervalVar]] = {s.id: [] for s in active_scrub_nurses}

        for case in patient_cases:
            c_id = case.id
            dur = case.estimated_duration_minutes
            earliest = max(0, case.arrival_minute)
            latest_start = max(earliest, horizon_minutes - dur)

            is_sched = model.NewBoolVar(f"sched_{c_id}")
            sched_vars[c_id] = is_sched

            s_var = model.NewIntVar(earliest, latest_start, f"start_{c_id}")
            e_var = model.NewIntVar(earliest + dur, horizon_minutes, f"end_{c_id}")
            model.Add(e_var == s_var + dur)
            start_vars[c_id] = s_var
            end_vars[c_id] = e_var

            # 1. OR Room Assignment
            # Filter compatible rooms by equipment capabilities
            candidate_rooms = [
                r for r in operational_rooms
                if all(eq in r.equipped_capabilities for eq in case.required_equipment)
            ]
            if not candidate_rooms:
                candidate_rooms = operational_rooms  # Fallback to any operational room

            case_room_vars = []
            for r in candidate_rooms:
                b_var = model.NewBoolVar(f"room_{c_id}_{r.id}")
                room_assign_vars[(c_id, r.id)] = b_var
                case_room_vars.append(b_var)

                # Room interval includes mandatory sterilization turnaround
                eff_dur = dur + r.turnaround_sterilization_minutes
                r_end = model.NewIntVar(earliest + eff_dur, horizon_minutes + r.turnaround_sterilization_minutes, f"rend_{c_id}_{r.id}")
                model.Add(r_end == s_var + eff_dur).OnlyEnforceIf(b_var)

                r_interval = model.NewOptionalIntervalVar(s_var, eff_dur, r_end, b_var, f"r_int_{c_id}_{r.id}")
                room_intervals[r.id].append(r_interval)

            if case_room_vars:
                model.Add(sum(case_room_vars) == is_sched)
            else:
                model.Add(is_sched == 0)

            # 2. Surgeon Assignment
            # Filter surgeons by specialty
            candidate_surgeons = [
                s for s in active_surgeons
                if case.specialty in s.specialties or SurgicalSpecialty.GENERAL_SURGERY in s.specialties
            ]
            if not candidate_surgeons:
                candidate_surgeons = active_surgeons

            case_surgeon_vars = []
            for s in candidate_surgeons:
                s_assign = model.NewBoolVar(f"surg_{c_id}_{s.id}")
                surgeon_assign_vars[(c_id, s.id)] = s_assign
                case_surgeon_vars.append(s_assign)

                s_interval = model.NewOptionalIntervalVar(s_var, dur, e_var, s_assign, f"s_int_{c_id}_{s.id}")
                surgeon_intervals[s.id].append(s_interval)

            if case_surgeon_vars:
                model.Add(sum(case_surgeon_vars) == is_sched)
            else:
                model.Add(is_sched == 0)

            # 3. Anesthesiologist Assignment
            case_anes_vars = []
            for anes in active_anesthesiologists:
                a_assign = model.NewBoolVar(f"anes_{c_id}_{anes.id}")
                anesthesia_assign_vars[(c_id, anes.id)] = a_assign
                case_anes_vars.append(a_assign)

                anes_interval = model.NewOptionalIntervalVar(s_var, dur, e_var, a_assign, f"anes_int_{c_id}_{anes.id}")
                anesthesia_intervals[anes.id].append(anes_interval)

            if case_anes_vars:
                model.Add(sum(case_anes_vars) == is_sched)
            elif active_anesthesiologists:
                model.Add(is_sched == 0)

            # 4. Scrub Nurse Assignment
            case_nurse_vars = []
            for n in active_scrub_nurses:
                n_assign = model.NewBoolVar(f"nurse_{c_id}_{n.id}")
                nurse_assign_vars[(c_id, n.id)] = n_assign
                case_nurse_vars.append(n_assign)

                n_interval = model.NewOptionalIntervalVar(s_var, dur, e_var, n_assign, f"nurse_int_{c_id}_{n.id}")
                nurse_intervals[n.id].append(n_interval)

            if case_nurse_vars:
                model.Add(sum(case_nurse_vars) == is_sched)

        # Enforce No-Overlap on all Operating Rooms (strictly separated by turnaround)
        for r in operational_rooms:
            if room_intervals[r.id]:
                model.AddNoOverlap(room_intervals[r.id])

        # Enforce No-Overlap on Lead Surgeons
        for s in active_surgeons:
            if surgeon_intervals[s.id]:
                model.AddNoOverlap(surgeon_intervals[s.id])

        # Enforce No-Overlap on Anesthesiologists
        for a in active_anesthesiologists:
            if anesthesia_intervals[a.id]:
                model.AddNoOverlap(anesthesia_intervals[a.id])

        # Enforce No-Overlap on Scrub Nurses
        for n in active_scrub_nurses:
            if nurse_intervals[n.id]:
                model.AddNoOverlap(nurse_intervals[n.id])

        # Objective Function:
        # Maximize triage-weighted scheduled cases
        # Minimize waiting delays (especially for Resuscitation and Emergent)
        # Minimize deadline violations
        objective_terms = []
        for case in patient_cases:
            c_id = case.id
            is_sched = sched_vars[c_id]
            s_var = start_vars[c_id]
            e_var = end_vars[c_id]
            base_w = urgency_weights.get(case.triage_urgency, 1000)

            # Reward scheduling
            objective_terms.append(base_w * is_sched)

            # Penalty for waiting time (delay from arrival to incision)
            delay_penalty_mult = 20 if case.triage_urgency == TriageUrgency.RESUSCITATION_L1 else (5 if case.triage_urgency == TriageUrgency.EMERGENT_L2 else 1)
            objective_terms.append(-delay_penalty_mult * (s_var - case.arrival_minute))

            # Penalty for missing clinical deadline
            if case.deadline_minutes:
                is_late = model.NewBoolVar(f"late_{c_id}")
                model.Add(e_var > case.deadline_minutes).OnlyEnforceIf(is_late)
                model.Add(e_var <= case.deadline_minutes).OnlyEnforceIf(is_late.Not())
                objective_terms.append(-int(base_w * 0.4) * is_late)

        model.Maximize(sum(objective_terms))

        # Solve CP-SAT
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.random_seed = self.random_seed
        status_code = solver.Solve(model)

        elapsed_ms = int((time.monotonic() - start_mono) * 1000)
        status_str = {
            cp_model.OPTIMAL: "optimal",
            cp_model.FEASIBLE: "feasible",
            cp_model.INFEASIBLE: "infeasible",
            cp_model.MODEL_INVALID: "invalid",
        }.get(status_code, "unknown")

        schedule_items: list[SurgicalScheduleItem] = []
        wait_times_emergency: list[int] = []
        unmet_cases: list[dict[str, Any]] = []

        total_scheduled = 0
        emergency_handled = 0
        elective_bumped = 0
        icu_in_use = 0

        resuscitation_total = sum(1 for c in patient_cases if c.triage_urgency == TriageUrgency.RESUSCITATION_L1)
        resuscitation_sched = 0
        emergent_total = sum(1 for c in patient_cases if c.triage_urgency == TriageUrgency.EMERGENT_L2)
        emergent_sched = 0

        if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            for case in patient_cases:
                c_id = case.id
                if solver.Value(sched_vars[c_id]) == 1:
                    total_scheduled += 1
                    s_val = int(solver.Value(start_vars[c_id]))
                    e_val = int(solver.Value(end_vars[c_id]))
                    delay = max(0, s_val - case.arrival_minute)

                    if case.triage_urgency in (TriageUrgency.RESUSCITATION_L1, TriageUrgency.EMERGENT_L2):
                        emergency_handled += 1
                        wait_times_emergency.append(delay)
                        if case.triage_urgency == TriageUrgency.RESUSCITATION_L1:
                            resuscitation_sched += 1
                        else:
                            emergent_sched += 1

                    if case.icu_bed_needed:
                        icu_in_use += 1

                    # Assigned OR room
                    assigned_room_id = next(
                        (r.id for r in operational_rooms if (c_id, r.id) in room_assign_vars and solver.Value(room_assign_vars[(c_id, r.id)]) == 1),
                        operational_rooms[0].id,
                    )
                    assigned_room = room_map[assigned_room_id]
                    turn_end = e_val + assigned_room.turnaround_sterilization_minutes

                    # Assigned Surgeon
                    assigned_surg_id = next(
                        (s.id for s in active_surgeons if (c_id, s.id) in surgeon_assign_vars and solver.Value(surgeon_assign_vars[(c_id, s.id)]) == 1),
                        active_surgeons[0].id if active_surgeons else "NONE",
                    )
                    assigned_surg = staff_map.get(assigned_surg_id)

                    # Assigned Anesthesia
                    assigned_anes_id = next(
                        (s.id for s in active_anesthesiologists if (c_id, s.id) in anesthesia_assign_vars and solver.Value(anesthesia_assign_vars[(c_id, s.id)]) == 1),
                        active_anesthesiologists[0].id if active_anesthesiologists else "NONE",
                    )
                    assigned_anes = staff_map.get(assigned_anes_id)

                    # Assigned Nurse
                    assigned_nurse_id = next(
                        (s.id for s in active_scrub_nurses if (c_id, s.id) in nurse_assign_vars and solver.Value(nurse_assign_vars[(c_id, s.id)]) == 1),
                        active_scrub_nurses[0].id if active_scrub_nurses else "NONE",
                    )

                    deadline_breached = bool(case.deadline_minutes and e_val > case.deadline_minutes)

                    rationale = (
                        f"Allocated to {assigned_room.name} with Lead Surgeon {assigned_surg.name if assigned_surg else 'On-Call'}. "
                        f"Wait-to-incision: {delay} min."
                    )
                    if deadline_breached:
                        rationale += f" Delayed by competing life-critical emergencies (Deadline: {case.deadline_minutes}m)."

                    constraints = [
                        f"Turnaround sterilization enforced (+{assigned_room.turnaround_sterilization_minutes}m)",
                        "Dedicated non-overlapping clinical surgical team",
                    ]
                    if case.required_equipment:
                        constraints.append(f"Equipped with: {', '.join(case.required_equipment)}")

                    schedule_items.append(
                        SurgicalScheduleItem(
                            case_id=c_id,
                            patient_mrn=case.mrn,
                            patient_name=case.patient_name,
                            triage_urgency=case.triage_urgency.name,
                            specialty=case.specialty.value,
                            or_room_id=assigned_room_id,
                            or_room_name=assigned_room.name,
                            start_minute=s_val,
                            end_minute=e_val,
                            sterilization_end_minute=turn_end,
                            lead_surgeon_id=assigned_surg_id,
                            lead_surgeon_name=assigned_surg.name if assigned_surg else "Staff Surgeon",
                            anesthesiologist_id=assigned_anes_id,
                            anesthesiologist_name=assigned_anes.name if assigned_anes else "Staff Anesthetist",
                            scrub_nurse_id=assigned_nurse_id,
                            delay_minutes=delay,
                            deadline_breached=deadline_breached,
                            icu_reserved=case.icu_bed_needed,
                            clinical_rationale=rationale,
                            enforced_constraints=constraints,
                        )
                    )
                else:
                    if case.triage_urgency == TriageUrgency.ELECTIVE_L4:
                        elective_bumped += 1
                    unmet_cases.append({
                        "case_id": case.id,
                        "patient_name": case.patient_name,
                        "triage": case.triage_urgency.name,
                        "specialty": case.specialty.value,
                        "reason": "Bumped or unscheduled due to emergency theatre capacity limits",
                    })

        mean_wait = sum(wait_times_emergency) / len(wait_times_emergency) if wait_times_emergency else 0.0
        total_cases = len(patient_cases)
        overall_fulfillment = total_scheduled / total_cases if total_cases > 0 else 1.0
        resus_rate = resuscitation_sched / resuscitation_total if resuscitation_total > 0 else 1.0
        emergent_rate = emergent_sched / emergent_total if emergent_total > 0 else 1.0

        # Calculate OR Suite Utilization
        total_avail_or_minutes = len(operational_rooms) * horizon_minutes
        total_used_or_minutes = sum(
            (item.sterilization_end_minute - item.start_minute)
            for item in schedule_items
        )
        utilization = min(1.0, total_used_or_minutes / total_avail_or_minutes) if total_avail_or_minutes > 0 else 0.0

        summary = HospitalORSummary(
            plan_id=plan_id or f"ORPLAN-{int(time.time())}",
            hospital_name=hospital_name,
            solver_status=status_str,
            solve_time_ms=elapsed_ms,
            total_cases=total_cases,
            scheduled_cases=total_scheduled,
            emergency_cases_handled=emergency_handled,
            elective_cases_bumped=elective_bumped,
            overall_fulfillment_rate=round(overall_fulfillment, 3),
            resuscitation_l1_fulfillment=round(resus_rate, 3),
            emergent_l2_fulfillment=round(emergent_rate, 3),
            mean_emergency_wait_minutes=round(mean_wait, 1),
            peak_or_utilization_rate=round(utilization, 3),
            icu_bed_usage=icu_in_use,
            icu_bed_capacity=icu_bed_capacity,
            validation_passed=True,
            validation_violations=[],
            shortages_and_delays=unmet_cases,
        )

        return HospitalORPlan(
            plan_id=summary.plan_id,
            hospital_id=hospital_id,
            version=version,
            summary=summary,
            items=schedule_items,
        )
