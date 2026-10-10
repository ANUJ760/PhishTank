<p align="center">
  <img src="gecompose.png" alt="GeCompose Hero Banner" width="100%" />
</p>

<p align="center">
  <b>Multimodal Constraint Intake &bull; Solver Guaranteed Schedules &bull; On-Chain Consent</b><br>
  <sub>Hacktoberfest Hack Day</sub>
</p>

<p align="center">
  <a href="https://ai.google.dev/gemma"><img src="https://img.shields.io/badge/Model-Gemma_4_(E4B_+_12B)-4285F4?style=flat-square&logo=google" alt="Gemma 4" /></a>
  <a href="https://developers.google.com/optimization"><img src="https://img.shields.io/badge/Solver-OR--Tools_CP--SAT-34A853?style=flat-square" alt="OR-Tools" /></a>
  <a href="https://ethereum.org"><img src="https://img.shields.io/badge/Ledger-Ethereum_EVM-627EEA?style=flat-square&logo=ethereum" alt="EVM" /></a>
  <a href="https://www.docker.com"><img src="https://img.shields.io/badge/Sandbox-Docker_Containers-2496ED?style=flat-square&logo=docker" alt="Docker" /></a>
</p>

---


## 1. Project Name

**GeCompose** (derived from *Gemma* and *composition*) is a smart scheduling system that coordinates three dedicated tools for what they do best:

- **Google Gemma 4** takes inputs from voice, photos, spreadsheets, and text, then explains scheduling conflicts in plain English.
- **Google OR-Tools CP-SAT** does the heavy math to guarantee 100% clash-free schedules.
- **Ethereum Smart Contract** ensures nobody can change someone's schedule without their signed permission.

---

## 2. Problem Statement

Every college timetable coordinator, lab manager, and event organizer faces the same nightmare:

| Pain Point | What Goes Wrong | Why Existing Tools Fail |
|---|---|---|
| **Scattered Inputs** | Constraints arrive via WhatsApp voice notes, whiteboard photos, paper slips, and messy Excel sheets. | Coordinators spend hours manually re-typing data, introducing human errors. |
| **Silent Failures** | Solvers just say "No Solution" or drop rules silently. | Nobody knows which two teachers clashed or who needs to compromise. |
| **No Consent Record** | Admins change slots unilaterally ("I never agreed to 8 AM Saturday!"). | Chat logs get deleted, spreadsheets get overwritten, and disputes drag on. |
| **LLMs Hallucinate** | Asking ChatGPT or an LLM to "build a timetable" fails. | Language models double-book classrooms and invent non-existent slots. |

---

## 3. Project Overview

GeCompose solves scheduling by giving each component one clear job:

```mermaid
flowchart LR
    A["Voice / Photos / Sheets"] --> B["Gemma 4\n(Extract Rules)"]
    B --> C["Human Confirm\n(Check Evidence)"]
    C --> D["CP-SAT Solver\n(Find Slots)"]
    D -->|"Feasible"| E["Published Schedule\n(Hash on Blockchain)"]
    D -->|"Conflict"| F["Gemma 4\n(Explain Clash)"]
    F --> G["Rule Owner Signs\n(Ethereum Contract)"]
    G --> D
```

### Clean Separation of Roles

| Component | What It Handles | What It Never Does |
|---|---|---|
| **Gemma 4** | Listens to audio, reads photos, writes sheet parsers, explains clashes | Never assigns slots or approves changes on its own |
| **CP-SAT Solver** | Places every class mathematically with zero overlaps | Never guesses human language or intent |
| **Ethereum Contract** | Stores rule ownership and records signed approvals | Never stores personal data or charges gas to view |

---

## 4. Proposed Solution

GeCompose runs a straightforward 6-step pipeline with human checkpoints at every critical step:

1. **Multimodal Intake:** Speak in English, Hindi, or Marathi, upload a photo of a whiteboard timetable, or drop an Excel sheet. Gemma 4 E4B extracts clean rules with proof tags (audio timestamps, image crops, spreadsheet cells).
2. **Automated Sheet Parsers:** For new spreadsheet layouts, Gemma 4 writes a small Python parser script and runs it in a safe Docker sandbox. Once verified, that parser is saved. Future files with that format run instantly with zero model tokens used.
3. **Review & Confirm:** You see every rule side-by-side with its source crop or audio playback. You click confirm before anything enters the solver.
4. **Mathematical Solving:** Google CP-SAT calculates a clash-free timetable. Hard rules are 100% satisfied by math.
5. **Plain-English Explanations:** If rules clash, CP-SAT pinpoints the exact conflicting subset. Gemma 4 tells you in plain English: "Prof. Rao cannot do Monday, but Section A Lab is pinned to Monday and only Prof. Rao can take it." It suggests solver-verified fixes.
6. **On-Chain Consent:** The affected teacher or coordinator approves the fix directly from their wallet. The final schedule hash is logged on Ethereum for a permanent, tamper-proof record.

---

## 5. Objectives

- **100% Valid Schedules:** Zero double-booked rooms or unavailable teacher clashes.
- **True Multimodal Support:** Voice, photos, and spreadsheets handled through Gemma 4 without chaining separate OCR or speech APIs.
- **Zero-Token Sheet Reuse:** Write spreadsheet parsers once; re-use them forever for free.
- **Clear Explanations:** When a schedule is impossible, explain exactly who clashed and why.
- **Tamper-Proof Audit Trail:** Rule changes require cryptographic signatures from rule owners.
- **Privacy by Default:** Audio, photos, and availability stay on your local machine; only secure hashes go on-chain.
- **Runs on a Laptop:** Intake runs on consumer GPUs (under 8 GB VRAM with 4-bit quantization).
- **Measurable Proof:** Show with real numbers that an LLM alone produces clashes while GeCompose produces none.

---

## 6. Target Users / Use Case

### Who Needs This?

- **College Department Coordinators:** Managing 50+ faculty members who submit availability over WhatsApp audio and paper notes.
- **Exam Cells:** Generating invigilation shifts where teachers demand fair rotation and zero overlaps.
- **Shared Research Labs:** Scheduling access to shared microscopes or computing clusters across competing departments.
- **Student Hackathons & Fests:** Allocating speaker slots, workshop rooms, and judging panels with last-minute speaker changes.

### A Real Example: The Monday Morning Clash

1. **Intake:** The coordinator speaks: "Prof. Rao cannot take Monday morning classes." They also upload `workload.xlsx`, which shows Prof. Rao is the only teacher for the Database Lab. Another note pins the Database Lab to Monday morning.
2. **Conflict:** CP-SAT reports that satisfying all three rules is impossible.
3. **Gemma 4 Explains:** "Database Lab is pinned to Monday, Prof. Rao is the only qualified instructor, but Prof. Rao is unavailable on Monday mornings."
4. **Verified Options:** Gemma 4 proposes:
   - **Option 1:** Move Database Lab to Tuesday 10 AM (Needs approval from Department Head).
   - **Option 2:** Add Prof. Mehta as co-instructor (Needs approval from Dean).
5. **Consent:** The Department Head approves Option 1 using their wallet. CP-SAT instantly re-solves with minimum disruption and publishes the final schedule.

---

## 7. Open-Source AI Technology Selected

### Google Gemma 4 Model Strategy

We use Google's open-weight **Gemma 4** family in a two-tier setup:

| Tier | Model | Size (4-bit) | Job | Why This Variant? |
|---|---|---|---|---|
| **Intake Tier** | **Gemma 4 E4B** | ~4.5 GB VRAM | Audio, photo, and text intake | Single model natively hears audio and reads images. Runs easily on laptop GPUs. |
| **Reasoning Tier** | **Gemma 4 12B** | ~7.2 GB VRAM | Writing sheet parsers and explaining conflicts | Better code synthesis for Python parsers and deeper reasoning for conflict graphs. |

Both models run locally using open-source inference runtimes like **vLLM** or **llama.cpp**.

---

## 8. Why This Technology Was Selected

- **One Model Family vs. Three Separate Tools:** Standard pipelines glue together Whisper (speech), Tesseract (OCR), and an LLM. When one makes a mistake, the whole pipeline breaks. Gemma 4 processes audio, images, and text in the same context window.
- **Native JSON Output:** Gemma 4 supports direct structured tool calling, outputting clean Pydantic data schemas without messy regex fixes.
- **Code Generation Saves Tokens:** Instead of feeding 2,000 Excel rows to an LLM every time (costing thousands of tokens), Gemma 4 writes a Python parser once. The Python script parses all future sheets in milliseconds at zero token cost.
- **Thinking Mode for Hard Conflicts:** Gemma 4's thinking mode is turned on only when explaining complex multi-party conflicts, keeping regular intake fast.
- **Runs Completely Offline:** Student and teacher availability data is personal. Running Gemma 4 locally means zero data leaves the building.

---

## 9. AI's Role in the System

Gemma 4 serves as the translator between humans and the mathematical solver.

```mermaid
flowchart TD
    subgraph Human["Human Inputs"]
        H1["Spoken Voice"]
        H2["Whiteboard Photos"]
        H3["Excel Sheets"]
    end

    subgraph AI["Gemma 4 Intelligence"]
        G1["Extracts Rules & Bounding Boxes"]
        G2["Synthesizes Python Sheet Parsers"]
        G3["Translates Solver Infeasibility to Plain English"]
    end

    subgraph Math["OR-Tools Solver"]
        S1["Calculates Slots Without Clashes"]
        S2["Pinpoints Minimal Unsatisfiable Core"]
    end

    Human --> AI --> Math
    Math -->|"When Clashes Happen"| AI -->|"Human-Actionable Choices"| Human
```

### What AI Does vs. What AI Never Does

- **Gemma 4 DOES:** Parse spoken Hindi/English, read photo notices, write safe parsing scripts, and explain why two rules clash.
- **Gemma 4 NEVER:** Assign slots directly, claim a schedule is valid without the solver, approve changes for someone else, or touch private keys.

---

## 10. System Architecture

```mermaid
flowchart TD
    subgraph INTAKE["1. Multimodal Intake"]
        V["Voice Audio"] --> G4["Gemma 4 E4B"]
        P["Roster Photos"] --> G4
        T["Typed Rules"] --> G4
        S["Spreadsheets"] --> CHK{"Known Sheet?"}
        CHK -- No --> GEN["Gemma 4 12B Code Gen"]
        GEN --> BOX["Docker Sandbox Test"]
        BOX --> RUN["Run Parser"]
        CHK -- Yes --> RUN
    end

    subgraph VERIFY["2. Confirm & Solve"]
        G4 --> UI["Side-by-Side Review Screen"]
        RUN --> UI
        UI --> SOLVE["OR-Tools CP-SAT Solver"]
    end

    subgraph CONFLICT["3. Infeasibility & Consent"]
        SOLVE -- Feasible --> CHECK["Independent Checker"]
        SOLVE -- Infeasible --> MUS["Minimal Conflict Extractor"]
        MUS --> EXP["Gemma 4 12B Explainer"]
        EXP --> SIGN["Rule Owner Signs On-Chain"]
        SIGN --> SOLVE
    end

    subgraph PUBLISH["4. Publication"]
        CHECK --> ETH["Anchor Hash to Ethereum"]
        ETH --> OUT["Interactive Grid & .ics Calendar Export"]
    end
```

---

## 11. Component-Level Architecture

| # | Subsystem | Inputs | Outputs | Tech Used |
|---|---|---|---|---|
| **1** | **Multimodal Intake** | Spoken audio, timetable photos, text | Structured draft rules with source pointers | Gemma 4 E4B |
| **2** | **Format Adapter** | `.xlsx` and `.csv` files | Clean rows with cell references | Docker Sandbox + Python |
| **3** | **Review Screen** | Draft rules + image crops / audio clips | Confirmed rules | Streamlit UI |
| **4** | **Constraint Registry** | Confirmed rules | Salted hashes and rule IDs | Local SQLite |
| **5** | **CP-SAT Solver** | Mathematical constraints, previous schedule (optional) | Complete schedule or conflict set | Google OR-Tools |
| **6** | **Gemma 4 Explainer** | Conflicting rule IDs | Plain-English summary + verified options | Gemma 4 12B |
| **7** | **Consent Contract** | Signed approvals from owners | On-chain status update | Solidity (`ConsentLedger.sol`) |
| **8** | **Schedule Publisher** | Verified timetable matrix | Timetable grid, `.ics` calendar files, proof page | Python + Web3.py |
| **9** | **Independent Checker** | Schedule + confirmed rules | Violation count (used for publishing and for the LLM-vs-GeCompose scoreboard) | Plain Python, no solver |

---

## 12. Data / Information Flow

```mermaid
sequenceDiagram
    autonumber
    actor Coordinator
    participant Gemma as Gemma 4 E4B
    participant Solver as OR-Tools CP-SAT
    participant Explainer as Gemma 4 12B
    actor Teacher as Rule Owner
    participant Chain as Ethereum Contract

    Coordinator->>Gemma: Voice Note + Roster Photo + Sheet
    Gemma->>Coordinator: Extracted Rules with Audio/Image Evidence
    Coordinator->>Solver: Confirmed Rules
    
    alt Schedule is Feasible
        Solver->>Chain: Publish Schedule Hash
    else Rules Conflict
        Solver->>Explainer: Return Exact Conflicting Rules
        Explainer->>Teacher: "Here is why your class clashed + 2 choices"
        Teacher->>Chain: Sign approval for Option 1
        Chain->>Solver: Rule updated on-chain -> Re-Solve
    end
```

### Privacy & Storage Breakdown

| Data Type | Where It Stays | Is It Ever Sent to Blockchain? |
|---|---|---|
| Voice recordings & photos | Local machine only | Never |
| Personal availability rules | Local machine only | Never |
| Rule hashes (salted) | Ethereum public ledger | Yes (32-byte cryptographic hash) |
| Published schedule hash | Ethereum public ledger | Yes (32-byte cryptographic hash) |
| Final timetable grid | Exported to `.ics` / PDF | Downloaded locally |

---

## 13. Agentic Workflow

GeCompose runs a bounded agentic loop with clear human guardrails:

```mermaid
flowchart LR
    A["Extract Rules"] --> B["Human Review Gate"]
    B --> C["CP-SAT Solver"]
    C -->|"Conflict"| D["Gemma 4 Diagnoses Clash"]
    D --> E["Solver Pre-Checks Fixes"]
    E --> F["Owner Signs On-Chain"]
    F --> C
    C -->|"Solved"| G["Publish Schedule"]
```

- **Strict Limits:** The loop runs at most 3 relaxation cycles. If stakeholders cannot agree after 3 tries, it stops and alerts the coordinator.
- **Safe Tools:** The AI agent can only inspect the conflict graph and test candidate fixes against the solver. It has zero access to wallet private keys.

---

## 14. Technology Stack

| Layer | Tool | License | Why We Picked It |
|---|---|---|---|
| **AI Models** | Google Gemma 4 (E4B & 12B) | Apache 2.0 | Native audio/vision handling, local weights, fast inference |
| **Local Inference** | llama.cpp / vLLM | MIT / Apache 2.0 | Runs 4-bit quantized models smoothly on laptop GPUs |
| **Constraint Solver** | Google OR-Tools CP-SAT | Apache 2.0 | Industry-standard discrete optimizer; mathematically guaranteed results |
| **Validation** | Pydantic v2 | MIT | Strict type enforcement for extracted constraints |
| **Code Sandbox** | Docker Engine | Apache 2.0 | Runs generated spreadsheet parsers with network access turned off |
| **Blockchain** | Solidity 0.8.24 + Foundry (Anvil) | MIT / Apache 2.0 | Local testnet with zero transaction fees and instant block mining |
| **Web3 Client** | Web3.py | MIT | Connects Python backend to the local Ethereum node |
| **Frontend UI** | Streamlit | Apache 2.0 | Interactive web UI with audio recording and image crop displays |

---

## 15. Expected Features

### Core Capabilities

- **Voice Ingestion:** Speak scheduling rules in mixed Hindi, Marathi, or English; Gemma 4 extracts structured rules with timestamps.
- **Photo Roster Scanning:** Upload photos of legacy paper timetables or whiteboard rosters with bounding-box highlighting.
- **One-Shot Sheet Parsers:** Gemma 4 writes Python code to parse custom Excel layouts; future sheets parse in milliseconds with zero tokens.
- **Zero Double-Bookings:** CP-SAT mathematically eliminates room and teacher overlaps.
- **Plain-English Explanations:** Explains schedule conflicts clearly, naming the exact people and constraints involved.
- **Pre-Verified Compromises:** Every proposed fix is tested against the solver before being shown to users.
- **Cryptographic Consent:** Changes require an on-chain signature from the affected person's wallet.
- **Public Schedule Verifier:** Anyone can drop a schedule file into a web page to verify its hash against the blockchain.
- **Calendar Feeds:** One-click export to `.ics` for Google Calendar, Outlook, and Apple Calendar.

### Advanced Features (Demo Differentiators)

- **Tamper-Evident Verifier:** Publish a schedule, change a single cell in the exported file, and drop it into the verifier. The hash no longer matches the on-chain record and the page turns red. This shows exactly why the ledger exists.
- **LLM-vs-GeCompose Scoreboard:** The same inputs are given to Gemma 4 alone ("build this timetable") and to the GeCompose pipeline. An independent checker counts double-bookings and rule violations in both outputs and shows the numbers side by side.
- **Minimal-Change Re-Solve:** After a rule changes, the solver re-solves with an objective that minimizes how many existing classes move. The UI reports "3 classes moved" instead of rebuilding the whole timetable.
- **Conflict Graph View:** The minimal conflicting rules are drawn as a small graph (for example Prof. Rao, Database Lab, Monday morning) with the clash highlighted, shown next to Gemma's plain-English explanation.
- **"Why Is This Class Here?" Button:** Click any cell in the timetable and see which rules forced that slot. Explainability for successful schedules, not only failed ones.
- **Live Hindi / Marathi Voice Rule:** A rule spoken in Hindi or Marathi is extracted live, with the audio clip attached as evidence.
- **Fairness Score (stretch):** Workload balance and teacher gap-time are tracked as soft constraints, with a before/after number.

---

## 16. Implementation Approach

Our engineering implementation divides the system into four decoupled modules, each with independent unit testing and integration criteria. A detailed backend build guide is in [`BACKEND_GUIDE.md`](BACKEND_GUIDE.md).

### Module 1: Multimodal Ingestion and Layout Parsing
- **Audio and Image Feature Lifting:** Stream raw microphone audio and document crops into Gemma 4 E4B using native structured tool calling. Map temporal references and visual regions to concrete time slots and room identifiers.
- **Sandboxed Parser Generation:** When an unindexed spreadsheet layout is uploaded, invoke Gemma 4 12B to write a standalone Python parsing function. Execute the script inside a network-isolated Docker container against 10 sample rows. Verify that outputs match the confirmed schema before caching the parser for recurring use.

### Module 2: Constraint Modeling and Conflict Isolation
- **Mathematical Scheduling Core:** Map confirmed Pydantic constraint records into Google OR-Tools CP-SAT Boolean decision variables. Formulate room capacities, instructor non-overlap, and session continuity as linear constraints.
- **Minimal Conflict Core Extraction:** When the constraint set is infeasible, trigger assumption-literal extraction in CP-SAT to isolate the exact minimal unsatisfiable subset (MUS) rather than returning a generic failure.
- **Minimal-Change Objective:** When a previous schedule exists, add an objective term that penalizes every session moved away from its previous slot.
- **Rule Provenance:** Every placed session records which rules constrain it, powering the "Why is this class here?" view.
- **Independent Checker:** A solver-free Python function re-validates any schedule (including an LLM-generated one) against the confirmed rules and returns the list of violations.

### Module 3: Smart Contract Consensus Protocol
- **ConsentLedger Deployment:** Implement and compile `ConsentLedger.sol` using Foundry, targeting an isolated local Anvil node with zero network fees.
- **Non-Repudiation Enforcement:** Restrict the `approveRelaxation` entrypoint so only the registered rule owner can sign off on changes. Anchor the final schedule hash immutably on-chain.

### Module 4: Coordinator Interface and Verification
- **Streamlit Frontend:** Build an interactive single-page dashboard featuring live audio capture, visual evidence crops, interactive timetable grids, conflict graph, and conflict resolution cards.
- **Client-Side Proof Checker:** Provide a standalone verification utility that re-computes local schedule hashes and queries the public ledger to guarantee authenticity, including a visible pass/fail result for tampered files.
- **Scoreboard Page:** Run the LLM-only baseline and the GeCompose pipeline on the same inputs and display violation counts side by side.

### Milestone Schedule and Validation Targets

| Engineering Sprint | Core Deliverable | Validation Mechanism | Success Benchmark |
|---|---|---|---|
| **Sprint 1: Core Solver & Schema** | Constraint models, CP-SAT solver, conflict extractor, independent checker, minimal-change objective | Synthetic benchmark test suite | 100% hard rule satisfaction on 50 test instances |
| **Sprint 2: Multimodal & Sandbox** | Gemma 4 E4B intake, Docker parser sandbox | Sample audio files and diverse Excel templates | > 95% parser synthesis accuracy within 3 attempts |
| **Sprint 3: On-Chain Consensus** | `ConsentLedger.sol`, Foundry unit test suite | Automated Anvil deployment scripts | Owner authorization reverts all non-owner calls |
| **Sprint 4: Frontend & Evaluation** | Streamlit UI, public proof portal, scoreboard, full integration | End-to-end integration test with user walkthrough | Sub-3-second rule extraction on laptop hardware |

---

## 17. Expected Final Output

1. **Interactive Web App:** A clean Streamlit application supporting microphone recording, image upload, spreadsheet drop, and live timetable grid visualization.
2. **Side-by-Side Evidence Inspector:** Click any rule to see the highlighted photo crop, audio player snippet, or spreadsheet cell it came from.
3. **Conflict Diagnostic Screen:** When rules clash, see a plain-English explanation, a conflict graph, the people involved, and one-click solver-tested fixes.
4. **Local Blockchain Explorer:** View the local Anvil event log showing rule registrations, signed approvals, and published schedule hashes.
5. **Universal Export:** Download verified timetables in interactive grid view, PDF, or `.ics` calendar format.
6. **Tamper Verifier Page:** Drop in a schedule file and get a clear match or mismatch against the on-chain hash.
7. **Scoreboard Page:** LLM-only vs GeCompose violation counts for the same inputs.

---

## 18. Future Scope / Scalability

- **Gasless Mobile Approvals (EIP-712):** Allow teachers to sign shift changes on their phones with FaceID/TouchID without needing crypto tokens or gas fees.
- **Zero-Knowledge Availability:** Use zero-knowledge proofs so teachers can prove they are available without revealing their personal calendars to administrators.
- **Cross-College Resource Sharing:** Connect multiple department nodes so two colleges can share auditoriums and laboratories fairly without a central boss.
- **PDF Timetable Extraction:** Extend one-shot parser synthesis to extract timetables trapped inside messy PDF documents.

---

## 19. Open-Source Dependencies / Components

| Component | Repository Link | License | Role |
|---|---|---|---|
| **Google Gemma 4** | [ai.google.dev/gemma](https://ai.google.dev/gemma) | Apache 2.0 | Multimodal intake, parser coding, conflict explanations |
| **Google OR-Tools** | [github.com/google/or-tools](https://github.com/google/or-tools) | Apache 2.0 | Discrete constraint optimization solver |
| **llama.cpp** | [github.com/ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) | MIT | Fast local 4-bit quantized inference |
| **Pydantic** | [docs.pydantic.dev](https://docs.pydantic.dev) | MIT | Data schema validation |
| **Foundry** | [book.getfoundry.sh](https://book.getfoundry.sh) | MIT / Apache 2.0 | Local Ethereum testnet (Anvil) & contract compiler |
| **OpenZeppelin** | [openzeppelin.com/contracts](https://www.openzeppelin.com/contracts) | MIT | Secure smart contract primitives |
| **Web3.py** | [web3py.readthedocs.io](https://web3py.readthedocs.io) | MIT | Python blockchain communication client |
| **Docker Engine** | [docker.com](https://www.docker.com) | Apache 2.0 | Isolated container sandbox for parsing scripts |
| **Streamlit** | [streamlit.io](https://streamlit.io) | Apache 2.0 | Interactive web user interface |
| **pandas & openpyxl** | [pandas.pydata.org](https://pandas.pydata.org) | BSD-3 / MIT | Tabular dataset processing |

---

## 20. Expected Challenges and Mitigation

| # | Challenge | Severity | Practical Mitigation |
|---|---|---|---|
| **1** | Spoken Dialect & Accents | Medium | Gemma 4 multilingual training + coordinator confirms every rule before solving. |
| **2** | Blurry Whiteboard Photos | Medium | Confidence scoring flags low-res crops and asks for manual confirmation. |
| **3** | Unsafe Generated Code | Critical | Generated Python parsers run in a container with **network access disabled** and strict timeouts. |
| **4** | Solver Stalling on Huge Schedules | High | 10-second solver timeout with soft-constraint relaxation heuristics. |
| **5** | Changed Spreadsheet Layouts | Medium | If more than 5% of rows fail, the system automatically triggers a re-synthesis of the parser. |
| **6** | Users Unfamiliar with Wallets | Medium | Pre-configured local test accounts for demo; roadmap adds gasless one-tap signatures. |
| **7** | Laptop GPU Memory Limits | High | Lightweight E4B model for intake; larger 12B model called only when a conflict occurs. |
| **8** | Live Demo Failure | High | Every Gemma call has a recorded-fixture fallback so the full flow can run without the model. |

---


---

## 21. Deterministic Engine & Conflict Diagnosis (Implemented)

The core deterministic processing engine of GeCompose is implemented in Python using **Google OR-Tools CP-SAT** and **Pydantic v2**, providing guaranteed clash-free schedule generation, conflict core diagnosis, and solver-verified alternative synthesis.

### Core Modules

- [`gecompose.models`](file:///home/blxnk/agy-workspace/PhishTank/gecompose/models.py): Strongly-typed domain models (`TimeSlot`, `Teacher`, `Room`, `Session`, `SchedulingProblem`, `ScheduledAssignment`, `ScheduleResult`, `ConflictDiagnosis`, `ScheduleAlternative`, `RelaxationPolicy`).
- [`gecompose.solver`](file:///home/blxnk/agy-workspace/PhishTank/gecompose/solver.py): CP-SAT discrete optimization solver (`CPSATScheduler`, `solve_schedule`) enforcing hard invariants with continuous timeline coordinates.
- [`gecompose.validator`](file:///home/blxnk/agy-workspace/PhishTank/gecompose/validator.py): Independent schedule verifier (`verify_schedule`) preventing any unverified or invalid schedule from being published.
- [`gecompose.diagnostics`](file:///home/blxnk/agy-workspace/PhishTank/gecompose/diagnostics.py): CP-SAT assumption-literal conflict diagnosis (`ConflictDiagnoser`, `diagnose_conflicts`) with deletion-based Minimal Unsatisfiable Subset (MUS) reduction.
- [`gecompose.alternatives`](file:///home/blxnk/agy-workspace/PhishTank/gecompose/alternatives.py): Solver-verified alternative generator (`AlternativeGenerator`, `generate_alternatives`) synthesizing distinct, minimal-penalty schedule alternatives by relaxing user preferences.

### Conflict Diagnosis & Infeasibility Cores

When a schedule request is mathematically unsatisfiable, GeCompose activates diagnostic assumption literals:
1. **Assumption Literals**: Every constraint (session requirements, teacher/room pinning, restrictions, qualifications, capacity, and availability) is guarded by a dedicated Boolean literal.
2. **Infeasibility Core Extraction**: CP-SAT extracts a sufficient unsatisfiable subset.
3. **Minimal Unsatisfiable Subset (MUS) Reduction**: A deletion-based filtering pass checks each core assumption. If all remaining assumptions are essential, `is_minimal` is marked `True`. If diagnosis times out before minimality is verified, `is_minimal` is accurately reported as `False`.
4. **Factual Explanations**: Diagnoses produce deterministic, fact-grounded explanations detailing the exact conflicting requirements without hallucination.

### Solver-Verified Alternative Generation

When a schedule is infeasible, GeCompose searches for valid alternative schedules:
- **Non-Negotiable Invariants**: Teacher non-overlap, room non-overlap, teacher availability, room availability, teacher qualifications, and room capacities are **always hard** and never relaxed.
- **Relaxable Requirements**: Pinned or allowed time slots, teachers, and rooms may be relaxed according to a configurable `RelaxationPolicy`.
- **Optimization**: CP-SAT minimizes the total relaxation penalty (e.g. preferring slot moves over teacher swaps).
- **Independent Double-Check**: Every synthesized alternative is independently verified against `verify_schedule` before being returned.

### Installation & Test Suite

```bash
# Set up virtual environment and install package in editable mode
python3 -m venv .venv
.venv/bin/pip install -e .

# Run the complete test suite
.venv/bin/pytest -v
```

---


### Project and Team Details

| Item | Details |
|---|---|
| **Project Title** | GeCompose |
| **Track** | 2. Best Use of Gemma 4 / Gemma 4 Open-Source|
| **Team Name** | PhishTank |
| **Members** | Rounak Mishra [@rounakkm](https://github.com/rounakkm) |
|             | Anuj Lulu [@ANUJ760](https://github.com/ANUJ760)       |
|             | Adarsh Jha [@Adarsh2709](https://github.com/Adarsh2709)|
|             | Shlok Tiwari [@1shhlok](https://github.com/1shhlok)    |


---
