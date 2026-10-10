"""Conflict-core minimization and solver verification of proposed changes."""
from backend.models import Roster, Rule
from backend.solver.model import solve

def shrink_core(roster: Roster, rules: list[Rule], core: list[str]) -> list[str]:
    by_id={r.id:r for r in rules}; current=list(dict.fromkeys(r for r in core if r in by_id))
    for rule_id in list(current):
        trial=[rid for rid in current if rid!=rule_id]
        if solve(roster,[by_id[rid] for rid in trial])[0]=="infeasible": current=trial
    return current

def verify_option(roster: Roster, rules: list[Rule], rule_id: str, new_params: dict) -> bool:
    patched=[r.model_copy(update={"params":new_params}) if r.id==rule_id else r for r in rules]
    return solve(roster,patched)[0]=="feasible"
