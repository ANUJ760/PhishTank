"""CP-SAT scheduling model with rule assumptions for conflict explanations."""
from __future__ import annotations
from collections import defaultdict
from ortools.sat.python import cp_model
from backend import config
from backend.models import Placement, Roster, Rule, Schedule

def build(roster: Roster, rules: list[Rule], prev: Schedule | None = None):
    model=cp_model.CpModel(); x={}; by_session=defaultdict(list); by_room=defaultdict(list); by_teacher=defaultdict(list)
    for session in roster.sessions:
        for teacher in session.teachers:
            for room in roster.rooms:
                if room.capacity < session.size: continue
                for day in range(config.DAYS):
                    for slot in range(config.SLOTS_PER_DAY):
                        key=(session.id,teacher,room.name,day,slot)
                        var=model.new_bool_var("x_"+"_".join(map(str,key)))
                        x[key]=var; by_session[session.id].append(var); by_room[(room.name,day,slot)].append(var); by_teacher[(teacher,day,slot)].append(var)
    for session in roster.sessions:
        if by_session[session.id]: model.add_exactly_one(by_session[session.id])
        else: model.add_bool_or([])
    for values in (*by_room.values(),*by_teacher.values()): model.add_at_most_one(values)
    literals={}
    for rule in rules:
        if rule.status != "confirmed": continue
        lit=model.new_bool_var("rule_"+rule.id); literals[rule.id]=lit; p=rule.params
        for (sid,teacher,room,day,slot),var in x.items():
            bad=(rule.type=="teacher_unavailable" and teacher==p["teacher"] and day==p["day"] and slot in p["slots"])
            bad |= (rule.type=="room_unavailable" and room==p["room"] and day==p["day"] and slot in p["slots"])
            bad |= (rule.type=="pin_session" and sid==p["session_id"] and not(day==p["day"] and slot in p["slots"]))
            bad |= (rule.type=="only_qualified" and sid==p["session_id"] and teacher not in p["teachers"])
            if bad: model.add(var==0).only_enforce_if(lit)
    model.add_assumptions(list(literals.values()))
    if prev is not None:
        previous={p.session_id:(p.session_id,p.teacher,p.room,p.day,p.slot) for p in prev.placements}
        terms=[]
        for sid,key in previous.items():
            var=x.get(key); terms.append(1-var if var is not None else 1)
        if terms: model.minimize(sum(terms))
    return model,x,literals

def solve(roster: Roster, rules: list[Rule], prev: Schedule | None=None):
    model,x,literals=build(roster,rules,prev); solver=cp_model.CpSolver()
    solver.parameters.max_time_in_seconds=config.SOLVER_TIME_S; solver.parameters.random_seed=config.SOLVER_SEED; solver.parameters.num_search_workers=1
    status=solver.solve(model)
    if status in (cp_model.OPTIMAL,cp_model.FEASIBLE):
        placements=[Placement(session_id=k[0],teacher=k[1],room=k[2],day=k[3],slot=k[4]) for k,v in x.items() if solver.value(v)]
        return "feasible",Schedule(placements=sorted(placements,key=lambda p:p.session_id)),None
    if status==cp_model.INFEASIBLE:
        by_index={lit.index:rid for rid,lit in literals.items()}
        indices=solver.sufficient_assumptions_for_infeasibility()
        return "infeasible",None,[by_index[i if i>=0 else -i-1] for i in indices if (i if i>=0 else -i-1) in by_index]
    return "unknown",None,None
