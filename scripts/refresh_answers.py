"""Answer-layer correction after Alpha (development project) browser review.

Retrieval selection stays frozen. Rerun the selected configuration with the
corrected answer layer, record new timings, and preserve original reports.
"""
import json
import sys
import shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas.corpus import ROOT,load_docs,load_questions
from atlas.retrieval import Config,Encoder,Index
from atlas.evaluate import run,save

selection=json.loads((ROOT/"reports/selection.json").read_text())
config=Config(**selection["selected"])
index=Index(load_docs(),Encoder(),semantic=config.chunking=="semantic",persist=False)
dev=[q for q in load_questions() if q.split=="dev"]
report=run(index,dev,config,routing=selection["router_enabled"],graph_enabled=selection["graph_enabled"])
save("answer-correction-development",report)
print("DEV ANSWER",json.dumps(report["summary"]),flush=True)
old=ROOT/"reports/heldout.json"
original=ROOT/"reports/heldout-before-answer-fix.json"
if not original.exists():
    shutil.copyfile(old,original)
report=json.loads(old.read_text())
test=[q for q in load_questions() if q.split=="test"]
report["selected"]=run(index,test,config,routing=selection["router_enabled"],graph_enabled=selection["graph_enabled"])
report["baseline"]=run(index,test,Config())
report["answer_layer_correction"]="Explicit named-project evidence filter; discovered on Alpha development demo; retrieval configuration unchanged. Original report retained."
save("heldout",report)
print("TEST ANSWER",json.dumps(report["selected"]["summary"]),flush=True)
