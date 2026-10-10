"""Canonical JSON, CSV and iCalendar exports."""
from __future__ import annotations
import csv, io
from datetime import date,datetime,timedelta,timezone
from backend import config
from backend.hashing import canonical,schedule_obj
from backend.models import Roster,Schedule

def json_bytes(schedule: Schedule) -> bytes: return canonical(schedule_obj(schedule)).encode("utf-8")
def csv_bytes(schedule: Schedule) -> bytes:
    output=io.StringIO(newline=""); writer=csv.writer(output,lineterminator="\r\n"); writer.writerow(["session_id","teacher","room","day","time"])
    for p in sorted(schedule.placements,key=lambda x:x.session_id):
        day=config.DAY_NAMES[p.day] if 0<=p.day<len(config.DAY_NAMES) else str(p.day)
        slot=config.SLOT_TIMES[p.slot] if 0<=p.slot<len(config.SLOT_TIMES) else str(p.slot)
        writer.writerow([p.session_id,p.teacher,p.room,day,slot])
    return output.getvalue().encode("utf-8")
def ics_bytes(schedule: Schedule,roster: Roster|None=None) -> bytes:
    start=date.fromisoformat(config.WEEK_START_MONDAY); sessions={s.id:s.course for s in roster.sessions} if roster else {}
    now=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"); lines=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//GeCompose//EN"]
    for p in sorted(schedule.placements,key=lambda x:(x.day,x.slot,x.session_id)):
        moment=datetime.combine(start+timedelta(days=p.day),datetime.strptime(config.SLOT_TIMES[p.slot],"%H:%M").time())
        end=moment+timedelta(hours=1); summary=f"{sessions.get(p.session_id,p.session_id)} ({p.teacher})"
        escape=lambda s:s.replace("\\","\\\\").replace(";",r"\;").replace(",",r"\,").replace("\n",r"\n")
        lines.extend(["BEGIN:VEVENT",f"UID:{p.session_id}-{schedule.version}@gecompose",f"DTSTAMP:{now}",f"SUMMARY:{escape(summary)}",f"LOCATION:{escape(p.room)}",f"DTSTART:{moment:%Y%m%dT%H%M%S}",f"DTEND:{end:%Y%m%dT%H%M%S}","END:VEVENT"])
    lines.append("END:VCALENDAR")
    return ("\r\n".join(lines)+"\r\n").encode("utf-8")
