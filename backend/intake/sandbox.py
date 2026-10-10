"""Run generated spreadsheet parser code in a constrained subprocess/container."""
from __future__ import annotations
import json, shutil, subprocess, sys, tempfile, uuid
from pathlib import Path
from backend import config

class SandboxError(RuntimeError): pass
RUNNER='''import sys,json,importlib.util\nd=sys.argv[1]\nspec=importlib.util.spec_from_file_location("parser",f"{d}/parser.py")\nm=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)\nprint(json.dumps(m.parse(f"{d}/input.xlsx")))\n'''
def run_parser(code: str, xlsx: Path, timeout_s: int=15) -> list[dict]:
    if not xlsx.is_file(): raise SandboxError("spreadsheet file does not exist")
    with tempfile.TemporaryDirectory(prefix="gecompose-parser-") as temp:
        folder=Path(temp); (folder/"parser.py").write_text(code,encoding="utf-8"); (folder/"runner.py").write_text(RUNNER,encoding="utf-8"); shutil.copyfile(xlsx,folder/"input.xlsx")
        name=f"gc-{uuid.uuid4().hex[:12]}"
        can_docker = (
            config.SANDBOX_MODE == "docker"
            and shutil.which("docker") is not None
            and not config.MOCK_LLM
        )
        if can_docker:
            img_check = subprocess.run(
                ["docker", "image", "inspect", config.SANDBOX_IMAGE],
                capture_output=True,
                check=False,
            )
            if img_check.returncode != 0:
                can_docker = False

        if can_docker:
            cmd = [
                "docker", "run", "--rm", "--name", name, "--network", "none",
                "--read-only", "--tmpfs", "/tmp:rw,noexec,nosuid,size=32m",
                "--memory", "256m", "--cpus", "1", "--pids-limit", "64",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                "-v", f"{folder}:/work:ro", config.SANDBOX_IMAGE,
                "python", "/work/runner.py", "/work"
            ]
        elif config.MOCK_LLM or config.ALLOW_LOCAL_SANDBOX or config.SANDBOX_MODE == "local":
            cmd = [sys.executable, str(folder / "runner.py"), str(folder)]
        else:
            raise SandboxError("Sandbox docker image not found and local execution is disabled")
        try: result=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout_s,check=False)
        except FileNotFoundError as exc: raise SandboxError("Docker executable was not found") from exc
        except subprocess.TimeoutExpired as exc:
            if config.SANDBOX_MODE=="docker": subprocess.run(["docker","kill",name],capture_output=True,timeout=3)
            raise SandboxError("parser timed out") from exc
        if result.returncode: raise SandboxError(result.stderr[-2000:] or "parser failed")
        try: value=json.loads(result.stdout)
        except json.JSONDecodeError as exc: raise SandboxError("parser did not print valid JSON") from exc
        if not isinstance(value,list) or any(not isinstance(row,dict) for row in value): raise SandboxError("parser output must be a list of objects")
        return value
