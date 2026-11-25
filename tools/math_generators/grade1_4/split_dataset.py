"""Create deterministic train and held-out JSONL splits without content overlap."""
import argparse, json
from pathlib import Path
from tools.math_generators.grade1_4 import TOPICS, generate, verify

TRAIN_BASE = 100_000
BENCH_BASE = 9_000_000_000
STRIDE = 10_000_000

def fingerprint(p):
    return (p["topic"], p["difficulty"], p["problem"].strip(), p["answer"].strip())

def make_records(topics, count, base, occupied):
    records=[]
    for index, topic in enumerate(topics):
        seed=base+index*STRIDE
        made=0
        while made<count:
            p=generate(seed,1+(made%5),topic)
            fp=fingerprint(p)
            if fp not in occupied:
                occupied.add(fp); records.append(p); made+=1
            seed+=1
    return records

def build(count_per_topic=100,out_dir="data/grade1_4"):
    if count_per_topic<1: raise ValueError("count_per_topic must be positive")
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    train_keys=set(); train=make_records(TOPICS,count_per_topic,TRAIN_BASE,train_keys)
    all_keys=set(train_keys)
    benchmark=make_records(TOPICS,count_per_topic,BENCH_BASE,all_keys)
    assert train_keys.isdisjoint({fingerprint(x) for x in benchmark})
    assert {x["id"] for x in train}.isdisjoint({x["id"] for x in benchmark})
    assert all(verify(x) for x in train+benchmark)
    for name,items in (("train.jsonl",train),("benchmark.jsonl",benchmark)):
        (out/name).write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in items),encoding="utf-8")
    manifest={"topics":list(TOPICS),"train_count":len(train),"benchmark_count":len(benchmark),
              "train_seed_base":TRAIN_BASE,"benchmark_seed_base":BENCH_BASE,
              "content_fingerprints_disjoint":True,"ids_disjoint":True}
    (out/"split_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--count-per-topic",type=int,default=100)
    parser.add_argument("--out",default="data/grade1_4")
    args=parser.parse_args()
    print(json.dumps(build(args.count_per_topic,args.out),indent=2))
