"""Opt-in local Lean proof artifact checker for Stage D.

Proof files are never executed during import or CI. The caller explicitly
invokes verify_lean_file, which launches Lean without a shell and with timeout.
"""
from __future__ import annotations
import re
import subprocess
from pathlib import Path

_NAME=re.compile(r"^[A-Za-z_][A-Za-z0-9_'.]*$")
_FORBIDDEN=re.compile(r"\b(?:sorry|admit)\b")

def _strip_lean_comments_and_strings(source:str)->str:
    """Replace nested block comments, line comments and strings with spaces."""
    out=[]; i=0; depth=0; in_string=False
    while i<len(source):
        if depth:
            if source.startswith("/-",i): depth+=1; out.extend("  "); i+=2
            elif source.startswith("-/",i): depth-=1; out.extend("  "); i+=2
            else: out.append("\n" if source[i]=="\n" else " "); i+=1
        elif in_string:
            if source[i]=="\\": out.extend("  "); i+=min(2,len(source)-i)
            elif source[i]=='"': out.append(" "); i+=1; in_string=False
            else: out.append("\n" if source[i]=="\n" else " "); i+=1
        elif source.startswith("/-",i): depth=1; out.extend("  "); i+=2
        elif source.startswith("--",i):
            while i<len(source) and source[i]!="\n": out.append(" "); i+=1
        elif source[i]=='"': in_string=True; out.append(" "); i+=1
        else: out.append(source[i]); i+=1
    if depth: raise ValueError("unterminated Lean block comment")
    if in_string: raise ValueError("unterminated Lean string")
    return "".join(out)

def preflight_lean_source(source:str,theorem_name:str)->dict:
    if not isinstance(source,str): raise TypeError("source must be text")
    if not isinstance(theorem_name,str) or not _NAME.fullmatch(theorem_name):
        raise ValueError("theorem_name must be a Lean identifier")
    code=_strip_lean_comments_and_strings(source)
    issues=[]
    if _FORBIDDEN.search(code): issues.append("source contains forbidden sorry/admit placeholder")
    if not re.search(r"\b(?:theorem|lemma)\s+"+re.escape(theorem_name)+r"\b",code):
        issues.append(f"source does not declare theorem or lemma {theorem_name}")
    return {"preflight_passed":not issues,"theorem_name":theorem_name,"issues":issues}

def verify_lean_file(path, theorem_name:str, *, lean_executable:str="lean", timeout_seconds:float=30.0)->dict:
    """Explicitly ask local Lean to type-check one source file; never shell-run."""
    file_path=Path(path)
    if file_path.suffix!=".lean": raise ValueError("proof file must have .lean extension")
    if isinstance(timeout_seconds,bool) or not isinstance(timeout_seconds,(int,float)) or not 0<timeout_seconds<=120:
        raise ValueError("timeout_seconds must be greater than 0 and at most 120")
    if not isinstance(lean_executable,str) or not lean_executable.strip() or "\n" in lean_executable:
        raise ValueError("lean_executable must be a non-empty executable path")
    try: source=file_path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"status":"file_error","verified":False,"theorem_name":theorem_name,"error":str(exc)}
    try: preflight=preflight_lean_source(source,theorem_name)
    except (TypeError,ValueError) as exc:
        return {"status":"preflight_error","verified":False,"theorem_name":theorem_name,"error":str(exc)}
    if not preflight["preflight_passed"]:
        return {"status":"rejected","verified":False,"theorem_name":theorem_name,"issues":preflight["issues"],"lean_invoked":False}
    try:
        result=subprocess.run([lean_executable,str(file_path)],capture_output=True,text=True,
                              timeout=float(timeout_seconds),check=False,shell=False)
    except FileNotFoundError:
        return {"status":"lean_unavailable","verified":False,"theorem_name":theorem_name,"lean_invoked":False}
    except subprocess.TimeoutExpired:
        return {"status":"timeout","verified":False,"theorem_name":theorem_name,"lean_invoked":True,"timeout_seconds":timeout_seconds}
    except OSError as exc:
        return {"status":"execution_error","verified":False,"theorem_name":theorem_name,"lean_invoked":False,"error":str(exc)}
    output=(result.stdout or "")+"\n"+(result.stderr or "")
    # Lean can accept 'sorry' with a warning; never accept a sorry-warning.
    if re.search(r"\b(?:declaration|uses).{0,80}\bsorry\b",output,re.IGNORECASE):
        return {"status":"rejected_sorry_warning","verified":False,"theorem_name":theorem_name,"lean_invoked":True,"returncode":result.returncode,"output":output[-4000:]}
    return {"status":"verified" if result.returncode==0 else "lean_failed",
            "verified":result.returncode==0,"theorem_name":theorem_name,
            "lean_invoked":True,"returncode":result.returncode,"output":output[-4000:],
            "limitations":["Verification applies only to the named theorem in this local Lean invocation and its imported environment.",
                          "This adapter does not search for proofs or translate natural-language claims.",
                          "A proof accepted by Lean does not establish that the theorem statement matches the intended problem."]}
