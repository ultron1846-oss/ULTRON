import argparse,json
from pathlib import Path
from .generators import TOPICS,generate,verify
TRAIN_BASE=200_000
BENCH_BASE=8_000_000_000
STRIDE=10_000_000
def fp(p):return (p["topic"],p["difficulty"],p["problem"].strip(),p["answer"].strip())
def records(count,base,seen):
 out=[]
 for i,topic in enumerate(TOPICS):
  seed=base+i*STRIDE; made=0
  while made<count:
   p=generate(seed,1+made%5,topic); seed+=1
   if fp(p) in seen:continue
   seen.add(fp(p));out.append(p);made+=1
 return out
def build(count_per_topic=100,out="data/grade5_8"):
 if count_per_topic<1:raise ValueError("count must be positive")
 path=Path(out);path.mkdir(parents=True,exist_ok=True); seen=set()
 train=records(count_per_topic,TRAIN_BASE,seen); train_ids={p["id"] for p in train}
 bench=records(count_per_topic,BENCH_BASE,seen)
 assert train_ids.isdisjoint({p["id"] for p in bench}) and all(verify(p) for p in train+bench)
 for name,data in (("train.jsonl",train),("benchmark.jsonl",bench)):
  (path/name).write_text("".join(json.dumps(p,ensure_ascii=False)+"\n" for p in data),encoding="utf-8")
 manifest={"topics":list(TOPICS),"train_count":len(train),"benchmark_count":len(bench),"train_seed_base":TRAIN_BASE,"benchmark_seed_base":BENCH_BASE,"fingerprint_overlap":0}
 (path/"split_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8");return manifest
if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--count-per-topic",type=int,default=100);parser.add_argument("--out",default="data/grade5_8");a=parser.parse_args();print(json.dumps(build(a.count_per_topic,a.out),indent=2))
