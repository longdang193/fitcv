from __future__ import annotations
import argparse
from pathlib import Path
import yaml

SKILL_ALLOWED={"name","description","required_reads","distribution_tier"}

def _meta(path: Path):
    text=path.read_text(encoding="utf-8",errors="ignore")
    if not text.startswith("---"): return None
    parts=text.split("---",2)
    value=yaml.safe_load(parts[1]) if len(parts)==3 else None
    return value if isinstance(value,dict) else None

def validate(root: Path) -> list[str]:
    findings=[]
    skills=list((root/".agents/skills").glob("*/SKILL.md"))
    for path in sorted(skills):
        meta=_meta(path)
        if meta is None:
            findings.append(f"{path}: missing frontmatter"); continue
        for key in ("name","description"):
            if not isinstance(meta.get(key),str) or not meta[key].strip(): findings.append(f"{path}: invalid {key}")
        if meta.get("name") != path.parent.name: findings.append(f"{path}: name must match folder")
        extra=set(meta)-SKILL_ALLOWED
        if extra: findings.append(f"{path}: unused metadata {sorted(extra)}")
        reads=meta.get("required_reads",[])
        if not isinstance(reads,list): findings.append(f"{path}: required_reads must be list")
        elif len(reads)>1: findings.append(f"{path}: more than one unconditional required read")
        else:
            for read in reads:
                if not (root/read).exists(): findings.append(f"{path}: missing required read {read}")
    return findings

def main(argv=None):
    parser=argparse.ArgumentParser(description="Validate lean skill metadata.")
    parser.add_argument("--repo-root",default=str(Path(__file__).resolve().parents[1]))
    args=parser.parse_args(argv)
    findings=validate(Path(args.repo_root))
    if findings:
        print("Agent metadata validation failed:")
        for finding in findings: print(f"- {finding}")
        return 1
    print("Agent metadata validation passed.")
    return 0

if __name__=="__main__": raise SystemExit(main())
