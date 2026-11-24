import hashlib
import hmac
import os
import tempfile
from pathlib import Path
import torch
from .config import NeuroSparseConfig

def _digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def save_checkpoint(path,model:torch.nn.Module,config:NeuroSparseConfig,optimizer=None,step:int=0):
    target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
    payload={"format_version":1,"config":config.to_dict(),"model":model.state_dict(),
             "step":int(step),"optimizer":optimizer.state_dict() if optimizer else None}
    fd,name=tempfile.mkstemp(prefix="."+target.name+".",suffix=".tmp",dir=target.parent); os.close(fd)
    tmp=Path(name)
    try:
        torch.save(payload,tmp)
        with tmp.open("rb") as f: os.fsync(f.fileno())
        digest=_digest(tmp); os.replace(tmp,target)
        target.with_suffix(target.suffix+".sha256").write_text(digest+"  "+target.name+"\n",encoding="utf-8")
        return {"path":str(target),"sha256":digest,"step":step}
    finally: tmp.unlink(missing_ok=True)

def load_checkpoint(path,model:torch.nn.Module,optimizer=None,map_location="cpu"):
    target=Path(path); manifest=target.with_suffix(target.suffix+".sha256")
    if not target.is_file() or not manifest.is_file(): raise FileNotFoundError("checkpoint/manifest missing")
    expected=manifest.read_text(encoding="utf-8").split()[0]; actual=_digest(target)
    if not hmac.compare_digest(expected,actual): raise ValueError("checkpoint integrity verification failed")
    payload=torch.load(target,map_location=map_location,weights_only=True)
    if payload.get("format_version")!=1: raise ValueError("unsupported checkpoint format")
    model.load_state_dict(payload["model"])
    if optimizer is not None and payload.get("optimizer") is not None: optimizer.load_state_dict(payload["optimizer"])
    return {"step":int(payload["step"]),"config":payload["config"],"sha256":actual}
