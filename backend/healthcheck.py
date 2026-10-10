"""Human-readable checks for configured local services."""
from __future__ import annotations
import argparse, json, shutil, subprocess
from pathlib import Path
from backend import config

def _command(command:list[str],timeout:int=3)->tuple[bool,str]:
    try:
        result=subprocess.run(command,capture_output=True,text=True,timeout=timeout,check=False)
        return result.returncode==0,(result.stdout or result.stderr).strip()[-500:]
    except (OSError,subprocess.TimeoutExpired) as exc:return False,str(exc)
def inspect()->dict[str,dict]:
    items={"mock_llm":{"ok":True,"detail":"Fixture mode enabled" if config.MOCK_LLM else "Fixture mode disabled; live inference configured"}}
    try:
        from backend.registry import db
        db.check_connection()
        items["postgres"]={"ok":True,"detail":"PostgreSQL connection is healthy"}
    except Exception as exc:
        items["postgres"]={"ok":False,"detail":str(exc)}
    for tier,url,model in (("intake",config.INTAKE_URL,config.INTAKE_MODEL),("reason",config.REASON_URL,config.REASON_MODEL)):
        if config.MOCK_LLM:items[f"{tier}_model"]={"ok":True,"detail":"Not required in mock mode"};continue
        try:
            from openai import OpenAI
            models=OpenAI(base_url=url,api_key="local",timeout=3).models.list(); names=[m.id for m in models.data]
            items[f"{tier}_model"]={"ok":model in names or not names,"detail":f"Connected to {url}; configured model {model}"}
        except Exception as exc:items[f"{tier}_model"]={"ok":False,"detail":str(exc)}
    docker=shutil.which("docker")
    if not docker:items["docker"]={"ok":config.SANDBOX_MODE=="local","detail":"Docker executable not found"}
    else:
        ok,detail=_command([docker,"info"]); image_ok,image_detail=_command([docker,"image","inspect",config.SANDBOX_IMAGE])
        items["docker"]={"ok":ok and image_ok,"detail":detail if not ok else image_detail if not image_ok else "Docker and sandbox image available"}
    return items
def main()->int:
    parser=argparse.ArgumentParser();parser.add_argument("--audio");args=parser.parse_args()
    items=inspect()
    for name,item in items.items():print(("OK" if item["ok"] else "FAIL")+f" {name}: {item['detail']}")
    if args.audio:
        try:
            from backend.intake.voice_photo import ingest_audio
            print(json.dumps([r.model_dump() for r in ingest_audio(Path(args.audio).read_bytes(),Path(args.audio).name)],ensure_ascii=False,indent=2))
        except Exception as exc:print(f"FAIL audio: {exc}");return 1
    return 0 if all(item["ok"] for item in items.values()) else 1
if __name__=="__main__":raise SystemExit(main())
