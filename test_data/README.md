# Multimodal Synthetic Test Datasets

This directory contains comprehensive, realistic synthetic test data across four domain scenarios designed to validate the **GeCompose** constraint optimization, multimodal ingestion, and conflict explainability pipeline.

---

## Directory Overview

```
test_data/
├── 01_university_academic/             # Academic timetabling & faculty workload
│   ├── faculty_workload_roster.xlsx     # Multi-sheet Excel workbook (Faculty, Rooms, Courses)
│   ├── faculty_availability.csv         # Faculty unavailability declarations
│   ├── dean_voice_memo.wav              # Valid 16kHz PCM WAV audio dictating scheduling constraints
│   ├── whiteboard_weekly_schedule.png   # 1200x800 timetable whiteboard image with sticky notes
│   ├── departmental_memo.txt            # Plaintext official memo with pinned sessions & qualifications
│   └── expected_rules.json              # Ground-truth expected extracted rules
├── 02_hospital_surgical_medops/        # Emergency hospital surgical suite optimization
│   ├── or_surgical_manifest.xlsx        # Operating theatres, case specialties, and sterilization buffers
│   ├── triage_cases.csv                 # Emergent (L1), Urgent (L2), and Elective (L3) patient cases
│   ├── trauma_dispatch_call.wav         # Valid 16kHz PCM WAV audio of ER trauma dispatch
│   ├── surgical_board_whiteboard.png    # 1200x800 OR surgical rotation whiteboard image
│   └── expected_plan.json               # Ground-truth Level-1 trauma benchmark metrics
├── 03_disaster_reliefops/              # Humanitarian relief logistics & fleet routing
│   ├── regional_depot_inventory.xlsx    # Warehouses & inventory stock (water, rations, medical, tents)
│   ├── relief_camps_requisition.csv     # Refugee/relief camp populations and resource demands
│   ├── vehicle_fleet_manifest.csv       # Transport vehicles, cargo payload capacities & ranges
│   ├── field_radio_transmission.wav     # Valid 16kHz PCM WAV audio of field radio requisition
│   └── expected_allocation.json         # Ground-truth equitable rationing targets
├── 04_conflicts_and_edge_cases/         # Infeasible scenarios triggering Minimal Unsatisfiable Cores (MUS)
│   ├── impossible_pinned_overlap.csv    # Conflicting matrix (two sessions pinned to same room & slot)
│   ├── faculty_clash_voicemail.wav      # Valid 16kHz PCM WAV voicemail with conflicting unavailability
│   ├── conflict_notice_photo.png        # 1000x600 bulletin photo highlighting conflicting assignments
│   └── expected_mus_core.json           # Ground-truth MUS core and relaxation options
└── generate_test_data.py                # Reproducible generator script
```

---

## Scenarios Breakdown

### Scenario 1: University Academic Timetabling (`01_university_academic`)
* **Objective:** Test end-to-end multimodal ingestion (Audio + Image + Excel + CSV + Text) and solve a weekly academic timetable.
* **Multimodal Assets:**
  * `faculty_workload_roster.xlsx`: Complete faculty directory (`Prof. Alice Vance`, `Prof. Bob Chen`, etc.), room capacities (`Room 101` (60), `Lab 202` (35)), and course catalog (`CS501`, `CS502`, etc.).
  * `dean_voice_memo.wav`: Synthesized 16kHz 16-bit mono audio simulating Dean Henderson dictating constraints (`CS501` pinned to Wednesday 10:00; `Lab 202` offline on Tuesday morning).
  * `whiteboard_weekly_schedule.png`: High-resolution rendered whiteboard grid highlighting pinned slots and room maintenance notices.
  * `departmental_memo.txt`: Textual confirmation of instructor qualifications and unavailabilities.
* **Expected Output:** Feasible schedule with zero room double-bookings, zero teacher overlaps, and 100% capacity adherence.

### Scenario 2: Hospital Emergency Surgical Suites (`02_hospital_surgical_medops`)
* **Objective:** Test the `MedOps` optimizer with trauma surgical suites, triage urgency tiers, and emergency preemption.
* **Multimodal Assets:**
  * `or_surgical_manifest.xlsx`: Multi-sheet catalog detailing Operating Theatres (`OR-TRAUMA-1`, `OR-CARDIAC-2`, `OR-GENERAL-3`), sterilization turnaround windows (20–30 min), and surgical cases.
  * `trauma_dispatch_call.wav`: Dispatch audio calling for immediate OR prep for an incoming Level-1 trauma resuscitation patient.
  * `surgical_board_whiteboard.png`: Color-coded surgical suite whiteboard with triage urgency tags (`RED: L1 Emergent`, `YELLOW: L2 Urgent`, `BLUE: L3 Elective`).
  * `triage_cases.csv`: Emergency admissions with duration estimates and required surgical roles (Lead Surgeon, Anesthesiologist, Scrub Nurse).
* **Expected Output:** Globally optimal `HospitalORPlan` ensuring 100% L1 emergency fulfillment, zero surgeon double-bookings, and strict sterilization buffer windows.

### Scenario 3: Disaster ReliefOps Supply Chain (`03_disaster_reliefops`)
* **Objective:** Test equitable, urgency-weighted supply allocation and transport vehicle routing during crisis events.
* **Multimodal Assets:**
  * `regional_depot_inventory.xlsx`: Warehouses and stock reserves for potable water, medical kits, emergency rations, and winterized tents.
  * `relief_camps_requisition.csv`: Field camp populations and urgent supply requisitions.
  * `field_radio_transmission.wav`: Emergency field radio audio from Camp River Alpha requesting life-critical water and medical kits.
  * `vehicle_fleet_manifest.csv`: 10-ton heavy trucks, all-terrain vehicles, and cargo helicopters with payload weight and volume limits.
* **Expected Output:** `AllocationPlan` calculating maximin equitable fulfillment ratios without exceeding transport payload limits.

### Scenario 4: Conflicts & Infeasibility Diagnostics (`04_conflicts_and_edge_cases`)
* **Objective:** Deliberately trigger solver infeasibility to test Minimal Unsatisfiable Subset (MUS) extraction and Gemma 12B plain-English relaxation suggestions.
* **Multimodal Assets:**
  * `impossible_pinned_overlap.csv`: Pinned sessions causing immediate room and teacher double-bookings.
  * `faculty_clash_voicemail.wav`: Voicemail declaring unavailability for a mandatory single-instructor session.
  * `conflict_notice_photo.png`: Bulletin notice highlighting the clashing rules.
* **Expected Output:** `status: "infeasible"`, identifying the exact conflicting rule subset and generating solver-verified relaxation options (`move_slot`, `swap_teacher_or_room`).

---

## How to Ingest & Test

### Option A: Via the Web Dashboard
1. Open the GeCompose Dashboard at `http://localhost:5173`.
2. Navigate to **Data Intake** (`/app/intake`).
3. Drag and drop any combination of files from `test_data/01_university_academic` (e.g. `.xlsx`, `.csv`, `.wav`, `.png`).
4. Click **Ingest & Extract Rules**.
5. Review the structured constraint cards generated on screen and click **Confirm Rules**.
6. Navigate to **Schedule** (`/app/schedule`) and click **Generate Schedule**.

### Option B: Via Python Test Runner
```bash
# Run the synthetic validation suite using these assets
MOCK_LLM=1 .venv/bin/pytest tests/test_all_structured_outputs_synthetic.py -v
```

### Option C: Re-generating or Refreshing Test Assets
```bash
.venv/bin/python test_data/generate_test_data.py
```
