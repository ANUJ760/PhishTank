"""GeCompose Interactive Frontend & Verification Portal.
Directly interfaces with backend.api.
"""
from __future__ import annotations
import json
from pathlib import Path
import streamlit as st
import pandas as pd

from backend import api, config
from backend.models import Rule, Schedule

st.set_page_config(
    page_title="GeCompose | AI-Assisted Timetable Engine",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .status-card {
        padding: 0.75rem 1rem;
        border-radius: 8px;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        margin-bottom: 0.5rem;
    }
    .badge-ok {
        background-color: #DCFCE7;
        color: #15803D;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #BBF7D0;
    }
    .badge-fail {
        background-color: #FEE2E2;
        color: #B91C1C;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 4px;
        border: 1px solid #FECACA;
    }
    .session-badge {
        padding: 8px;
        border-radius: 6px;
        background: #EFF6FF;
        border-left: 4px solid #3B82F6;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def load_health():
    try:
        h = api.health()
        return h.items
    except Exception as e:
        return {"error": {"ok": False, "detail": str(e)}}


health = load_health()

# Top Sidebar Controls
with st.sidebar:
    st.image("gecompose.png", use_container_width=True) if Path("gecompose.png").is_file() else st.title("GeCompose")
    st.markdown("### Quick Demo Setup")
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🌱 Seed Demo", use_container_width=True):
            with st.spinner("Seeding database and initial schedule..."):
                try:
                    api.seed_demo()
                    st.success("Seeded!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    with col_s2:
        if st.button("🧹 Reset Demo", use_container_width=True):
            with st.spinner("Resetting demo state..."):
                try:
                    api.reset_demo()
                    st.info("Reset complete!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    st.markdown("---")
    st.markdown("### Backend Status")
    for key, val in health.items():
        ok = val.get("ok", False)
        detail = val.get("detail", "")
        badge = '<span class="badge-ok">ONLINE</span>' if ok else '<span class="badge-fail">OFFLINE</span>'
        st.markdown(f"**{key.upper()}** {badge}<br><small style='color: #64748B;'>{detail[:50]}</small>", unsafe_allow_html=True)


# Main Content Tabs
st.markdown('<div class="main-header">GeCompose Timetable Engine & Proof Portal</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Constraint-Satisfaction Scheduling with Multi-Party Consent & Deterministic Verification</div>', unsafe_allow_html=True)

tabs = st.tabs([
    "📅 Timetable Grid",
    "⚠️ Conflict Studio",
    "📥 Rule Management",
    "🛡️ Proof Portal & Verifier",
    "📊 Evaluation Scoreboard",
    "📜 Audit Log",
    "🩺 System Health"
])


# ---------------- TAB 1: Timetable Grid ----------------
with tabs[0]:
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        st.markdown("#### Solver Controls")
        min_change = st.checkbox("Minimal Change Mode", value=True, help="Preserves unaffected assignments when rules shift")
        if st.button("⚡ Solve Schedule (CP-SAT)", type="primary", use_container_width=True):
            with st.spinner("Running Google OR-Tools CP-SAT solver..."):
                res = api.solve(minimal_change=min_change)
                if res.status == "feasible":
                    st.success(f"Feasible schedule found in {res.solve_ms} ms! {len(res.moved)} sessions moved.")
                    st.rerun()
                elif res.status == "infeasible":
                    st.error(f"Infeasible! Conflict core: {res.conflict.rule_ids if res.conflict else 'Unknown'}")
                    st.session_state["active_conflict"] = res.conflict
                else:
                    st.warning(f"Solver returned: {res.status}. {res.message}")

        if st.button("📋 Publish Schedule", use_container_width=True):
            try:
                pub = api.publish()
                st.success(f"Published Version {pub.version}! Hash: {pub.hash[:16]}... Recorded in verified registry!")
                st.download_button("Download JSON", data=pub.json_bytes, file_name=f"schedule_v{pub.version}.json", mime="application/json")
                st.download_button("Download CSV", data=pub.csv_bytes, file_name=f"schedule_v{pub.version}.csv", mime="text/csv")
                st.download_button("Download ICS Calendar", data=pub.ics_bytes, file_name=f"schedule_v{pub.version}.ics", mime="text/calendar")
            except Exception as e:
                st.error(f"Publish failed: {e}")

    with col_t1:
        sched = api.db.latest_schedule()
        if sched:
            st.markdown(f"### Current Schedule (Version {sched.version})")
            days = config.DAY_NAMES
            slots = config.SLOT_TIMES
            grid_data = {day: ["" for _ in slots] for day in days}

            for p in sched.placements:
                if 0 <= p.day < len(days) and 0 <= p.slot < len(slots):
                    grid_data[days[p.day]][p.slot] = f"**{p.session_id}**<br>👤 {p.teacher}<br>📍 {p.room}"

            df = pd.DataFrame(grid_data, index=slots)
            st.markdown(df.to_html(escape=False), unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("#### Cell Explanation Inspector ('Why this assignment?')")
            sessions = [p.session_id for p in sched.placements]
            selected_session = st.selectbox("Select Session to inspect:", sessions)
            if selected_session:
                influences = api.why_cell(selected_session)
                if influences:
                    st.info(f"Session **{selected_session}** is constrained by {len(influences)} confirmed rule(s):")
                    for r in influences:
                        st.markdown(f"- **{r.id}** ({r.type}) by *{r.owner}*: `{r.params}`")
                else:
                    st.write(f"No specific restricting rules pinned to {selected_session}; assigned to satisfy global capacity & teacher availability.")
        else:
            st.info("No active schedule found in database. Click 'Seed Demo' or 'Solve Schedule' to generate one.")


# ---------------- TAB 2: Conflict Studio ----------------
with tabs[1]:
    st.markdown("### Conflict Core Isolation & Multi-Party Consent Simulation")
    st.markdown("Demonstrating how GeCompose handles impossible timetable constraints without arbitrary AI overrides.")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("#### Step 1: Inject Clashing Unavailability")
        st.write("Add Rule R3: Prof. Rao becomes unavailable on Monday Morning (Slots 0-2), creating a direct conflict with pinned DB_LAB (R1) and Dean's qualification rule (R2).")
        if st.button("🚨 Inject Rule R3 (Prof. Rao Unavailable)", type="primary"):
            r3 = Rule(
                id="R3",
                type="teacher_unavailable",
                owner="Prof. Rao",
                params={"teacher": "Prof. Rao", "day": 0, "slots": [0, 1, 2]},
                status="draft"
            )
            api.db.save_rule(r3)
            api.confirm_rule("R3")
            st.warning("Rule R3 registered in registry and confirmed! Solving now...")
            res = api.solve()
            if res.status == "infeasible":
                st.session_state["active_conflict"] = res.conflict
                st.error(f"Infeasibility Detected! Minimal Conflict Core: {res.conflict.rule_ids}")
            st.rerun()

    with col_c2:
        st.markdown("#### Step 2: AI Conflict Analysis")
        conflict = st.session_state.get("active_conflict")
        if not conflict:
            # check if current confirmed rules clash
            res = api.solve()
            if res.status == "infeasible":
                conflict = res.conflict

        if conflict:
            st.error(f"Active Conflict Core: **{', '.join(conflict.rule_ids)}** | Involving Owners: **{', '.join(set(conflict.owners))}**")
            if st.button("🧠 Explain Conflict & Propose Solver-Verified Options"):
                with st.spinner("Generating explanations and mathematically verifying options..."):
                    exp = api.explain_conflict(conflict)
                    st.session_state["active_explanation"] = exp
                    st.rerun()
        else:
            st.success("No active conflicts! The current rule set is feasible.")

    # Step 3: Relaxation Options & Approvals
    explanation = st.session_state.get("active_explanation")
    if explanation:
        st.markdown("---")
        st.markdown(f"#### Step 3: Verified Relaxation Options ({len(explanation.options)} Available)")
        st.info(f"**AI Summary:** {explanation.summary}")

        for opt in explanation.options:
            with st.expander(f"Option {opt.id}: Modify {opt.rule_id} ({opt.description})", expanded=True):
                st.write(f"**Required Approver:** `{opt.approver}`")
                st.write(f"**Proposed Parameters:** `{json.dumps(opt.new_params)}`")
                st.write(f"**Option Hash:** `{opt.option_hash}`")

                col_ap1, col_ap2, col_ap3 = st.columns([1, 1, 1])
                with col_ap1:
                    test_user = st.selectbox(f"Select Signer for {opt.id}:", ["Prof. Rao", "Coordinator", "Dean", "Dept Head"], key=f"user_{opt.id}")
                with col_ap2:
                    if st.button(f"Sign & Approve as {test_user}", key=f"btn_app_{opt.id}"):
                        res = api.approve_option(opt.id, as_user=test_user)
                        if res.ok:
                            st.success(f"Approved! Recorded in consent ledger (Ref: {res.tx_hash}).")
                        else:
                            st.error(f"Approval rejected: {res.error}")
                with col_ap3:
                    if st.button(f"Apply Option {opt.id} to Schedule", key=f"btn_apply_{opt.id}"):
                        try:
                            updated = api.apply_option(opt.id)
                            st.success(f"Applied! Rule {updated.id} updated. Resolving schedule...")
                            st.session_state.pop("active_conflict", None)
                            st.session_state.pop("active_explanation", None)
                            api.solve()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Cannot apply: {e}")


# ---------------- TAB 3: Rule Management ----------------
with tabs[2]:
    st.markdown("### Active & Draft Rules Ledger")
    rules = api.list_rules()
    if rules:
        rule_table = []
        for r in rules:
            rule_table.append({
                "ID": r.id,
                "Type": r.type,
                "Owner": r.owner,
                "Status": r.status,
                "Parameters": json.dumps(r.params),
                "Evidence": ", ".join(f"{e.kind}: {e.ref}" for e in r.evidence)
            })
        st.dataframe(pd.DataFrame(rule_table), use_container_width=True)
    else:
        st.write("No rules currently in registry.")

    st.markdown("---")
    st.markdown("#### Ingest Spreadsheet Rules (Docker Sandbox)")
    upload_file = st.file_uploader("Upload Excel Spreadsheet (.xlsx)", type=["xlsx"])
    if upload_file:
        if st.button("Parse in Sandbox"):
            with st.spinner("Synthesizing parser & running in secure Docker sandbox..."):
                try:
                    res = api.ingest_sheet(upload_file.getvalue(), upload_file.name)
                    st.success(f"Extracted {len(res.rules)} rules in {res.seconds:.2f}s! (Cache hit: {res.cache_hit}, Tokens used: {res.tokens_used})")
                    st.rerun()
                except Exception as e:
                    st.error(f"Parser error: {e}")


# ---------------- TAB 4: Proof Portal ----------------
with tabs[3]:
    st.markdown("### Public Timetable Proof & Integrity Verifier")
    st.markdown("Verify that a published schedule has not been altered since being cryptographically registered in the schedule registry.")

    verify_tab1, verify_tab2 = st.columns(2)
    with verify_tab1:
        st.markdown("#### Verify JSON File")
        verify_upload = st.file_uploader("Upload Schedule JSON to Verify", type=["json"], key="v_upload")
        if verify_upload:
            v_res = api.verify_file(verify_upload.getvalue())
            if v_res.match:
                st.success(f"✅ SCHEDULE IS AUTHENTIC & REGISTERED!\nRecomputed Hash: {v_res.recomputed_hash}")
            else:
                st.error(f"❌ VERIFICATION FAILED: {v_res.error or 'Hash mismatch with registry.'}")

    with verify_tab2:
        st.markdown("#### Tamper Detection Demo")
        latest = api.db.latest_schedule()
        if latest:
            st.write(f"Active Schedule Version: **{latest.version}**")
            col_d1, col_d2 = st.columns(2)
            with col_d1:
                if st.button("Test Original Schedule", use_container_width=True):
                    res = api.verify_file(api.export.json_bytes(latest))
                    if res.match:
                        st.success(f"Original Validated: {res.recomputed_hash[:16]}... is registered!")
            with col_d2:
                if st.button("Test Tampered Schedule (Altered Slot)", use_container_width=True):
                    # Tamper one slot
                    raw = json.loads(api.export.json_bytes(latest).decode("utf-8"))
                    if raw.get("placements"):
                        raw["placements"][0]["slot"] = (raw["placements"][0]["slot"] + 1) % 6
                    tampered_data = json.dumps(raw).encode("utf-8")
                    res = api.verify_file(tampered_data)
                    if not res.match:
                        st.error(f"Tampering Caught! Hash {res.recomputed_hash[:16]}... NOT found in registry!")
        else:
            st.info("Publish a schedule first to run tamper checks.")


# ---------------- TAB 5: Scoreboard ----------------
with tabs[4]:
    st.markdown("### GeCompose vs Unconstrained LLM Benchmark")
    st.markdown("Evaluating schedule constraint satisfaction violations across multiple runs.")
    num_runs = st.slider("Number of benchmark runs:", min_value=1, max_value=5, value=3)
    if st.button("🚀 Run Scoreboard Benchmark", type="primary"):
        with st.spinner("Executing comparative runs..."):
            sb = api.run_scoreboard(runs=num_runs)
            st.markdown("#### Results")
            rows = []
            for r in sb.rows:
                rows.append({
                    "Run #": r.run,
                    "GeCompose Violations (CP-SAT)": r.gecompose_violations,
                    "Baseline LLM Violations": r.baseline_violations,
                    "Baseline Clash Details": "; ".join(r.baseline_details[:2]) if r.baseline_details else "None"
                })
            st.table(pd.DataFrame(rows))


# ---------------- TAB 6: Audit Log ----------------
with tabs[5]:
    st.markdown("### Consent Ledger & System Audit Log")
    st.markdown("Immutable record of rule registrations, stakeholder approvals, and published schedule hashes.")
    try:
        events = api.chain_events()
        if events:
            ev_list = []
            for e in reversed(events):
                ev_list.append({
                    "Event": e.get("event"),
                    "ID": e.get("block"),
                    "Arguments": json.dumps(e.get("args", {}))
                })
            st.dataframe(pd.DataFrame(ev_list), use_container_width=True)
        else:
            st.info("No events logged yet. Perform a rule confirmation or schedule publish to generate events.")
    except Exception as e:
        st.error(f"Could not load audit events: {e}")


# ---------------- TAB 7: System Health ----------------
with tabs[6]:
    st.markdown("### System Health Diagnostics")
    for key, val in health.items():
        ok = val.get("ok", False)
        status_color = "green" if ok else "red"
        st.markdown(f"#### :{status_color}[{'●' if ok else '■'}] {key.replace('_', ' ').title()}")
        st.write(val.get("detail", "N/A"))
