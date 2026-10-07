# Sanyojan

**A consent-aware scheduler where Gemma 4 listens, reads and explains, a solver decides, and Ethereum records who agreed.**

Hacktober Fest Open Source AI Hackathon | Track 2: Best Use of Gemma 4

> **Summary:** Sanyojan accepts scheduling rules through voice notes, photographs, spreadsheets or typed text. A constraint solver builds a schedule that satisfies every hard rule. When rules conflict, Gemma 4 explains the conflict in plain language, identifies exactly who is affected, and only those individuals can approve the resolution. Every approval is recorded on Ethereum.

---

## 1. Project Name

**Sanyojan** (Sanskrit/Hindi for "coordination" or "arrangement"): Multimodal, Consent-Aware Scheduling with Gemma 4.

---

## 2. Problem Statement

Timetables, duty rosters, exam invigilation lists and shared-lab bookings are still built by a coordinator working across multiple spreadsheets. Four problems persist:

1. **Scattered formats.** Constraints are spread across WhatsApp voice notes, handwritten forms, photographs of previous timetables, and spreadsheets with varying layouts. Transferring all of this into a single tool introduces errors.
2. **Unexplained failures.** When rules cannot all be satisfied, existing tools report "no solution" or silently discard a rule without identifying *which* rules conflict or *who* owns them.
3. **No tamper-proof consent record.** Disputes follow schedule changes ("I never agreed to Saturday"). Chat messages and spreadsheet edits can be lost or rewritten by the same coordinator whose conduct is in question.
4. **Language models cannot guarantee valid schedules.** A language model asked to produce a timetable directly can violate stated rules. A constraint solver, by contrast, produces schedules that satisfy hard rules by construction.

In addition, availability data is personal. Individuals do not want it uploaded to third-party cloud services.

---

## 3. Project Overview and Solution

Sanyojan converts voice, photograph, spreadsheet and text input into a verified schedule. When the rules cannot all be satisfied, it converts each infeasibility into an approval request sent to the owners of the conflicting rules.

### Separation of Duties

| Component | Responsibility | Does not |
|---|---|---|
| **Gemma 4** | Understands voice, photographs and text; writes parsers for new spreadsheet layouts; explains conflicts; proposes resolutions | Place classes in slots, certify schedules, or approve changes |
| **Solver (OR-Tools CP-SAT)** | Finds valid schedules; identifies the minimal set of conflicting rules; re-checks every proposed resolution | Interpret human language |
| **Ethereum (ConsentLedger)** | Stores constraint ownership and hashes; accepts approvals only from the registered owner; records published schedule hashes | Hold funds, store personal data, or verify schedule correctness |

### Flow

1. **Intake:** The coordinator speaks, uploads photographs or screenshots, uploads spreadsheets (.xlsx or .csv), or types. Gemma 4 converts all inputs into structured constraint objects, each linked to its source (audio timestamp, image region, text span, or spreadsheet cell). For a spreadsheet layout that has not been seen before, Gemma 4 writes a parser once. The stored parser handles all subsequent files of the same layout without requiring further model calls.
2. **Confirm:** Every extracted constraint is displayed alongside its source evidence and a plain-language paraphrase. A human confirms it before it is registered.
3. **Solve:** The solver builds a schedule or reports that the constraints are infeasible.
4. **Explain:** If the constraints are infeasible, the solver returns the minimal conflicting subset. Gemma 4 explains the conflict and proposes ranked relaxations, each of which the solver re-checks for feasibility.
5. **Consent:** Each proposed relaxation is sent to the owner of the affected rule. The owner approves or rejects it on-chain.
6. **Publish:** Once all required approvals are received and the independent checker confirms zero violations, the schedule hash is published on-chain.

All AI inference runs locally on open-weight models.

### Solution Layers

| Layer | Description |
|---|---|
| Multimodal intake | Gemma 4 converts voice, images and text into constraint objects through function calling |
| Format adapter (parser synthesis) | Gemma 4 writes and tests a Python parser for each new spreadsheet layout. Stored parsers handle subsequent files of the same layout without using any model tokens |
| Confirmation screen | Displays each constraint alongside its source evidence and paraphrase |
| Constraint registry | Stores each constraint with its owner, type (hard or soft), and a salted hash |
| Solver (CP-SAT) | Builds schedules that guarantee all hard rules are satisfied |
| Conflict extractor | Identifies the minimal subset of rules that conflict |
| Gemma 4 explainer | Explains conflicts and ranks proposed relaxations |
| Consent contract | Enforces owner-only approval and maintains an append-only history |
| Publisher and verifier | Exports timetable grids and calendar files; provides a verification page that compares a file hash against the on-chain value |
| Evaluation harness | Measures extraction accuracy, rule violations, and explanation quality |

---

## 4. Objectives

- Accept scheduling rules through **voice, image and text** using a single open model family.
- Parse spreadsheets using **stored, tested parsers**. Each layout requires a model call only the first time it appears.
- Guarantee **zero hard-rule violations** in every published schedule.
- When the constraints are infeasible, **identify the exact conflicting rules and their owners** and propose solver-verified resolutions.
- Make every change **consent-based and auditable** through on-chain recording.
- Keep personal data **private** through local inference, with only salted hashes stored on-chain.
- Run on **modest hardware** (a laptop-class GPU for the smaller tier).
- Accept mixed **Hindi, Marathi and English** speech, with extraction accuracy reported per language.
- Deliver a **reproducible evaluation** under the Apache 2.0 license.

---

## 5. Target Users and Use Cases

| User | Need |
|---|---|
| College timetable cells and department coordinators | Build and revise class timetables from scattered inputs |
| Exam cells | Invigilation duties and seating plans with fairness and conflict rules |
| Shared-lab and inter-college resource managers | Resource booking among parties who do not fully trust a single administrator |
| Hostels, NGOs and volunteer groups | Duty rosters collected through chat messages and voice notes |
| Event organisers (hackathons, college fests) | Session and room schedules with speaker availability constraints |

**Core use case:** A coordinator dictates rules in Hindi and English, uploads a photograph of last year's timetable and the room list, and receives a verified schedule. When two rules conflict, their owners receive a plain-language explanation and approve a resolution.

---

## 6. Open-Source AI Technology Selected

**Primary model family: Google Gemma 4** (open weights, **Apache 2.0**).

According to the official model card, Gemma 4 is available in five sizes (**E2B, E4B, 12B, 26B A4B, 31B**) with context windows ranging from 128K to 256K tokens. All variants accept text and image input. Audio input is supported on the E2B, E4B and 12B variants. The family provides a thinking mode, native function calling, and support for over 140 languages.

| Role in Sanyojan | Variant | Reason |
|---|---|---|
| **Intake:** converts voice, image and text into constraints | **E4B**, 4-bit quantised (approximately 4.5 GB) | Handles audio, image and text within a single model |
| **Reasoning:** conflict explanation, relaxation ranking, parser writing | **12B** or **26B A4B** (approximately 6.7 to 14.4 GB at 4-bit) | Provides stronger reasoning and code generation capabilities |

**Supporting components** (see Section 13 for the full stack): OR-Tools CP-SAT, Pydantic, pandas, openpyxl, a container-based sandbox, Foundry, OpenZeppelin, web3.py or ethers.js, and Streamlit or Gradio.

*Note: Exact checkpoint names and memory figures will be confirmed against the official model card at the start of the final round.*

---

## 7. Why This Technology Was Selected

- **One model family for three input types.** A pipeline of separate speech recognition, OCR and language model components passes plain text between stages, losing cross-modal context. Gemma 4 receives audio and images within the same session.
- **Native function calling** allows the model to emit schema-valid constraint objects directly.
- **Code generation** enables parser synthesis, with a sandbox and automated tests checking every generated parser.
- **Token savings from stored parsers.** Per-row extraction incurs token costs proportional to the number of rows. Parser synthesis is a one-time cost that does not depend on file size. Subsequent files with the same layout require zero model tokens.
- **Thinking mode, used selectively.** The thinking mode is activated only when explaining complex conflicts that benefit from deeper reasoning.
- **Local and private.** The Apache 2.0 license permits unrestricted institutional use. Personal data remains on the coordinator's machine.
- **Multilingual.** Gemma 4 supports Hindi, Marathi and English code-mixing. Extraction accuracy is measured separately for each language.
- **A range of model sizes that fit a single laptop.** The smaller model handles high-volume intake, and the mid-size model is called only when a conflict requires explanation.

**Why the model does not build the schedule:** Hard rules must hold in every output, and language models provide no such guarantee. The evaluation includes a language-model-only baseline that counts hard-rule violations for comparison.

---

## 8. AI's Role in the System

Gemma 4 serves as the **interface between people and the solver**. It converts human input into the solver's constraint format, and converts the solver's output into explanations that people can act on.

**What the AI does:**
1. **Multimodal constraint extraction.** Converts voice, photographs and text into structured constraint objects with source pointers and confidence scores.
2. **Parser synthesis.** Writes Python parsers for new spreadsheet layouts and rewrites them when tests fail. Stored parsers handle all subsequent files of the same layout.
3. **Clarifying questions.** Asks for clarification when input is ambiguous.
4. **Paraphrase for confirmation.** Restates each constraint in plain language so that a human can verify correctness.
5. **Conflict explanation.** Explains why a set of rules cannot all be satisfied, naming the people and rules involved.
6. **Relaxation proposals.** Suggests ranked resolutions, using the solver as a feasibility-checking tool.
7. **Change summaries.** Writes the human-readable summary attached to each published version.

**What the AI does not do:** assign classes to slots, declare a schedule valid, approve any change, submit on-chain transactions, or read individual spreadsheet rows once a parser has passed its tests.

---

## 9. System Architecture

```mermaid
flowchart TD
    A["Voice note"] --> D
    B["Photo or screenshot"] --> D
    C["Typed text"] --> D
    D["Gemma 4 E4B intake"]
    D --> E["Confirmation screen"]
    S["Spreadsheet or CSV"] --> Q{"Parser stored?"}
    Q -->|"yes"| R["Stored parser (no model call)"]
    Q -->|"no"| W["Gemma 4 12B/26B writes parser"]
    W --> R
    R --> E
    E --> F["Constraint registry"]
    F --> G["CP-SAT solver"]
    G -->|"feasible"| K["Candidate schedule"]
    G -->|"infeasible"| H["Conflict extractor"]
    H --> I["Gemma 4 12B/26B: explanation + relaxations"]
    I --> J["Solver re-checks proposals"]
    J --> L["Proposals sent to owners"]
    L --> M["Ethereum consent contract"]
    M --> F
    K --> N["Independent checker"]
    N --> O["Publish: schedule hash on-chain"]
    O --> P["Outputs: grid, calendar, verification page"]
```

**Round lifecycle:**

```mermaid
stateDiagram-v2
    [*] --> Collecting
    Collecting --> Solving: constraints confirmed
    Solving --> Resolved: feasible
    Solving --> Conflict: infeasible
    Conflict --> AwaitingConsent: relaxations proposed
    AwaitingConsent --> Solving: all owners approved
    AwaitingConsent --> Conflict: an owner rejected
    Resolved --> Published: checker passes
    Published --> [*]
```

The contract records three on-chain states: Open (covering Collecting, Solving, Resolved, Conflict off-chain), AwaitingConsent, and Published.

### Architectural Decisions

| # | Decision | Reason |
|---|---|---|
| AD-1 | Solver is the only component that assigns classes to slots | Hard rules must hold in every output |
| AD-2 | Extracted constraints are human-confirmed before registration | A misread rule is caught before it changes a schedule |
| AD-3 | Ethereum contract enforces owner-only approval | Coordinator cannot approve on an owner's behalf or edit history |
| AD-4 | Only hashes on-chain | Personal data stays off-chain |
| AD-5 | Model process holds no private key or consent-calling tools | Consent actions exist only as human-signed transactions |
| AD-6 | Consent layer uses a five-call interface | Solver, checker and Gemma 4 tiers are decoupled from the consent implementation |
| AD-7 | Spreadsheets parsed by stored, immutable parsers | A layout costs model tokens only once; same file always gives same output |
| AD-8 | Parser code runs only in an isolated sandbox | Generated code is untrusted until tested |

---

## 10. Component-Level Architecture

| # | Component | Responsibility | Inputs | Outputs |
|---|---|---|---|---|
| 1 | **Multimodal intake** | Convert audio, images and text into constraint objects via function calling | Voice, photos, text | Draft constraints with sources and confidence |
| 1a | **Format adapter** | Write/test/store parsers for spreadsheet layouts; run stored parsers in sandbox | .xlsx/.csv files | Constraint objects with cell sources |
| 2 | **Confirmation screen** | Show each constraint beside its evidence and paraphrase | Draft constraints | Confirmed constraints |
| 3 | **Constraint registry** | Assign owner, type (hard/soft), salted hash | Confirmed constraints | Registered constraints |
| 4 | **Solver** | Build schedule satisfying hard rules | Registered constraints | Schedule or "infeasible" |
| 5 | **Conflict extractor** | Find minimal conflicting rule subset | Infeasible model | Conflicting subset and owners |
| 6 | **Explainer** | Explain conflict; generate and verify relaxation candidates | Conflicting subset | Explanation and ranked proposals |
| 7 | **Consent contract** | Enforce owner-only approval; append-only history | Proposals; signed transactions | Event log, published hashes |
| 8 | **Independent checker** | Re-verify every hard rule against final schedule | Schedule and constraints | Pass/fail with violations |
| 9 | **Publisher** | Export grid, calendar files, verification page | Final schedule | Outputs and verification |
| 10 | **Evaluation harness** | Reproducible scoring | Gold test sets | Metrics and ablation report |

**Constraint object fields:** identifier, owner, hard/soft, type, parameters, penalty weight (soft), source (modality + pointer), extraction confidence, paraphrase.

**Initial constraint types:** unavailability, daily/consecutive limits, required consecutive slots (labs), room capacity/type, pinned assignments, no double-booking, spread rules, required breaks, soft preferences.

### Format Adapter: Parser Synthesis

*Scope:* .xlsx and .csv inputs. PDF tables are future scope (Section 16).

*Layout fingerprint:* hash of sheet names + normalized header rows. Same fingerprint → same stored parser.

*Synthesis loop (reasoning-tier Gemma 4):*
1. Model receives header row, up to 10 sample rows, constraint schema, and output contract (function returning constraint-object JSON with source cells).
2. Gemma 4 writes the parser; sandbox runs it on the sample.
3. Human reviews parsed sample, corrects wrong rows → corrected rows become test cases.
4. Tests: (a) output matches confirmed rows; (b) Pydantic schema validation; (c) every object has a source cell; (d) no non-empty row silently dropped.
5. On failure, Gemma 4 reads the test report and rewrites (max 3 attempts). After that, fall back to per-row extraction.
6. Passing parser is stored with fingerprint, source code, hash, test rows, and model version.

*Owner labels:* parser outputs owner labels (e.g., faculty names). Coordinator maintains a label → Ethereum address table.

*Layout drift:* new fingerprint triggers synthesis. For known fingerprints, >5% skipped non-empty rows (configurable) flags the file for re-synthesis.

*Sandbox:* separate process in a container with network disabled, read-only access to the one uploaded file, CPU/memory/time limits, JSON stdout only. Static import check (allowlist: pandas, openpyxl, re, datetime, json) runs before execution.

### Blockchain Layer: `ConsentLedger`

One Solidity contract performing five functions:

1. **Registers constraint ownership** - stores owner address and constraint hash.
2. **Enforces owner-only approval** - reverts calls from any non-owner address.
3. **Blocks publication while consent is pending.**
4. **Keeps append-only history** - timestamped events that cannot be edited.
5. **Answers verification queries** - read-only lookup of published schedule hashes.

| Function | Caller | Effect |
|---|---|---|
| `registerConstraint(owner, contentHash)` | Admin | Creates constraint record. Emits `ConstraintRegistered`. |
| `openRound()` | Admin | Creates Open round. |
| `proposeRelaxation(roundId, constraintId, newContentHash, explanationHash)` | Admin | Creates Pending proposal; round → AwaitingConsent. |
| `approveRelaxation(proposalId)` | **Owner only** | Marks Approved; updates constraint hash. |
| `rejectRelaxation(proposalId)` | **Owner only** | Marks Rejected; constraint unchanged. |
| `publishSchedule(roundId, scheduleHash, constraintSetHash, summaryHash)` | Admin | Stores hashes + timestamp; round → Published. |
| `getConstraint(constraintId)` (view) | Anyone | Returns owner, hash, status. |
| `getPublication(scheduleHash)` (view) | Anyone | Returns round, hashes, timestamp. |

**Hashing (keccak256):**
- *Constraint hash:* canonical JSON + random 32-byte salt (prevents brute-force matching of low-entropy constraints).
- *Schedule hash:* canonical CSV with fixed column/row order.
- *Constraint-set hash:* concatenated constraint hashes in ID order.

**Not on-chain:** names, availability, constraint text, audio, images, schedule contents, explanation text.

**Deployment:** local Foundry (Anvil) chain with pre-funded test accounts. Optional Sepolia. No mainnet, no real funds.

**Why blockchain instead of a database:** the coordinator who operates the scheduler is also the party whose conduct is disputed. Three properties a coordinator-operated database cannot provide:
1. **Authorization the coordinator doesn't control** - `approveRelaxation` reverts unless sender is the registered owner.
2. **History the coordinator cannot rewrite** - past blocks cannot be edited.
3. **Verification independent of the scheduler's server** - anyone hashes a file and calls `getPublication` on a public node.

---

## 11. Data / Information Flow

```mermaid
sequenceDiagram
    participant C as Coordinator
    participant G as Gemma 4 E4B (intake)
    participant R as Registry
    participant S as Solver
    participant X as Gemma 4 12B (explainer)
    participant O as Owners
    participant E as Ethereum contract
    C->>G: Voice note, photos, text
    G->>C: Constraints with evidence and paraphrases
    C->>R: Confirm, edit or reject
    R->>S: Registered constraints
    alt feasible
        S->>E: Schedule hash after checker passes
    else infeasible
        S->>X: Minimal conflicting subset
        X->>S: Candidate relaxations to test
        S->>X: Which candidates are feasible
        X->>O: Explanation and ranked proposals
        O->>E: Approve or reject (signed by each owner)
        E->>R: Approved relaxations update constraints
        R->>S: Solve again
    end
    E->>C: Published version and verification page
```

**Illustrative example** (fictional names):

- Coordinator says in Hinglish: "Rao sir Monday ko available nahi hain. Section A ka DBMS lab Monday ko hi rakhna hai." A photo of last year's timetable and the department's workload sheet (.xlsx) are also uploaded.
- Three rules extracted: (C1) Prof. Rao unavailable Mondays, (C2) Section A DBMS lab pinned to Monday, (C3) only Prof. Rao teaches that lab. C1 and C2 from voice; C3 from the workload sheet (parsed by a newly synthesized parser).
- Solver: infeasible. Minimal conflicting subset: {C1, C2, C3}.
- Gemma 4 explains: "Section A's lab must be on Monday, only Prof. Rao teaches it, and Prof. Rao is unavailable on Mondays." Proposes: (R1) move lab to Tuesday (needs C2 owner's approval), (R2) allow a second teacher (needs C3 owner's approval). Solver confirms both feasible.
- Only the named owner approves on-chain. Solver re-runs, checker passes, schedule hash published.

---

## 12. Agentic Workflow

Sanyojan uses a **bounded** agentic loop:

1. **Extract:** intake model proposes constraints; asks clarifying questions when ambiguous.
2. **Confirm:** human accepts, edits or rejects each constraint.
3. **Solve and diagnose:** solver builds a schedule or returns the minimal conflicting subset.
4. **Explain and propose:** reasoning-tier model explains the conflict, generates relaxations, calls solver to test each.
5. **Consent:** each affected owner signs `approveRelaxation` or `rejectRelaxation` on-chain. Rejection returns to step 4 with that option excluded.
6. **Repeat, then stop:** at most three relaxation rounds per conflict. If unresolved, the system reports to the coordinator for manual decision.

**Tools the model may call:** add draft constraint, ask clarifying question, fetch conflict details, test relaxation with solver, write change summary, submit parser for sandbox testing, read test report.

**Guardrails:** the model process holds no private key and no tool that calls approve, reject or publish. Every model-proposed relaxation is solver-verified before anyone sees it.

---

## 13. Technology Stack

| Area | Choice |
|---|---|
| AI models | Gemma 4 E4B (intake), Gemma 4 12B or 26B A4B (explanation) |
| Local inference | Ollama, llama.cpp or vLLM (whichever supports Gemma 4 audio/image best) |
| Structured output | Native function calling + Pydantic |
| Solver | Google OR-Tools CP-SAT |
| Spreadsheets & sandbox | pandas, openpyxl; containerized sandbox with network disabled |
| Smart contract | Solidity 0.8.x (`ConsentLedger`); Foundry + OpenZeppelin AccessControl |
| Chain access | web3.py or ethers.js |
| Network | Local Anvil chain (primary); optional Sepolia. No mainnet |
| Interface | Streamlit or Gradio with audio/image upload |
| Outputs | Timetable grid, ICS calendar files, verification page |
| Evaluation | Python scripts, scikit-learn, matplotlib |
| Packaging | Docker, pinned dependencies, fixed random seeds |
| License | Apache 2.0, public GitHub repository |

---

## 14. Implementation Approach

Work is organized in tiers. Each module is independent, so any one can slip without breaking the core loop.

**Tier 1: Working core (must have)**
1. Constraint schema and registry.
2. Text intake with Gemma 4 E4B and confirmation screen.
3. CP-SAT solver, independent checker, timetable grid output.
4. Conflict extractor and Gemma 4 explanation with solver-verified relaxations.
5. Evaluation harness with a first test set.

**Tier 2: Multimodal intake and consent layer (should have)**
6. Voice intake (Gemma 4 audio input).
7. Image intake for timetable photos, availability forms, room lists.
8. Format adapter: parser synthesis, sandbox, parser registry.
9. Consent contract with tests, local chain, owner-approval flow.
10. Verification page.

**Tier 3: Polish (nice to have)**
11. Sepolia testnet deployment.
12. Hindi/Marathi explanations; calendar export.
13. Ablation report and polished demo script.

### Evaluation Plan

| What | How |
|---|---|
| Extraction accuracy | Gold set across typed text, spoken audio (including Hindi-English mixes), and photographed forms; precision, recall and field-level accuracy per modality and language |
| Parser synthesis | Set of spreadsheet layouts with hand-checked files. Metrics: parser pass rate within 3 attempts, repair attempts needed, exact-match rate, missed errors, token usage comparison vs. per-row extraction |
| Schedule validity | Independent checker on every output; LLM-only baseline counting rule violations |
| Conflict diagnosis | Explanation matches solver's minimal conflicting subset; human clarity rating |
| Proposal quality | Share of proposals that are feasible, with and without solver verification |
| Contract behavior | Foundry tests: non-owner approve/reject reverts, non-admin register/publish reverts, publish reverts while pending, events carry expected arguments, gas per function |
| Efficiency | Time per stage, memory use, tokens per model call |
| Ablations | Remove confirmation, voice, image, solver verification, or stored parsers; report accuracy/time/model-call changes |

---

## 15. Expected Final Output

1. A **working web app** accepting voice, images, spreadsheets and text, producing verified schedules.
2. A **conflict view** with clashing rules, owners, explanation and solver-verified fixes.
3. A **smart contract** with tests on a local chain (optionally Sepolia), plus consent log view.
4. A **verification page** checking any timetable file against the on-chain record.
5. **Exports:** timetable grid and calendar files.
6. A **reproducible evaluation report** with LLM-only baseline and ablations.
7. A **public GitHub repository** under Apache 2.0.

---

## 16. Future Scope

- **Shared institutions:** one consent ledger across departments/colleges for shared resources.
- **Gasless approvals:** `approveRelaxationBySig` with EIP-712 signatures so owners need no crypto.
- **Privacy-preserving proofs:** ZK proofs that a schedule satisfies rules without revealing availability.
- **Fairness reporting:** distribution of soft-rule costs across people.
- **More domains:** hospital rosters, volunteer shifts, event programmes.
- **More file formats:** PDF tables via the same synthesis loop.
- **Mobile and offline:** small Gemma 4 tier supports on-premise deployment.
- **Learning from corrections:** coordinator edits improve extraction accuracy.
- **Larger models:** leverage long context of bigger Gemma 4 sizes for full documents.

---

## 17. Open-Source Dependencies

| Component | Purpose | License |
|---|---|---|
| Gemma 4 (E4B, 12B, 26B A4B) | Intake and explanation | Apache 2.0 |
| Ollama / llama.cpp / vLLM | Local inference | MIT / MIT / Apache 2.0 |
| Google OR-Tools | CP-SAT solver | Apache 2.0 |
| Pydantic | Schema validation | MIT |
| pandas, openpyxl | Spreadsheet reading | BSD / MIT |
| Docker Engine | Parser sandbox | Apache 2.0 |
| Foundry | Contract tests and local chain | MIT / Apache 2.0 |
| OpenZeppelin Contracts | Access control | MIT |
| Solidity compiler (solc) | Contract compilation | GPL-3.0 |
| web3.py / ethers.js | Chain access | MIT |
| Streamlit / Gradio | Interface | Apache 2.0 |
| scikit-learn, matplotlib | Metrics and plots | BSD / PSF-style |

*License types will be re-verified when dependencies are pinned.*

---

## 18. Challenges and Mitigation

| Challenge | Mitigation |
|---|---|
| **Misread rules from voice or photos** | Evidence-linked confirmation, paraphrases, confidence flags, clarifying questions; per-modality accuracy measurement |
| **Low-quality photos** | Ask for clearer photo or typed correction; mark low-confidence fields |
| **Hindi/Marathi speech accuracy** | Measure per language on gold set; route low-confidence speech to typed confirmation |
| **Untrusted model-written code** | Containerized sandbox with network disabled, resource limits, import allowlist |
| **Parser passes tests but misreads other rows** | Summary review per file (counts, first 10 rows, skipped rows); evaluation counts missed errors |
| **Layout changes after parser stored** | Changed headers → new fingerprint → new synthesis; >5% skipped rows triggers re-synthesis |
| **Irreparable parser** | Fall back to per-row extraction; flag for manual review |
| **Model mis-formalizes a rule** | Schema validation, paraphrase round-trip, human confirmation |
| **Model proposes unworkable fix** | Every proposal solver-verified before display |
| **Admin can publish arbitrary hash** | Parties run independent checker; constraint-set hash recomputable from contract |
| **Owners without wallets** | Demo uses pre-funded test accounts; EIP-712 relay planned |
| **Testnet faucets unreliable** | Local Foundry chain is primary; Sepolia optional |
| **Contract bugs** | OpenZeppelin, Foundry tests, no payable functions, test network only, "not audited" notice |
| **Personal data exposure** | Local inference; only salted hashes on-chain |
| **Hackathon time limit** | Tiered plan; core loop works without voice, image, parsers or contract |
| **Hardware limits** | E4B intake runs on laptop GPU; explanation tier can run quantized 12B |

---

*Team details, contact information and the license file will be added to the repository metadata. This repository intentionally contains only this README, per the qualifier rules.*
# PhishTank
