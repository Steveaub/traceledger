import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from atlas.corpus import ROOT,DATA,load_docs,write_jsonl
from atlas.schema import Question
from atlas.retrieval import Config,Encoder,Index
from atlas.evaluate import run,save

samples=[
 ("What phases does the FEMP microgrid development checklist cover?","doe-microgrid-checklist",["planning","design","procurement","implementation"]),
 ("Who is the microgrid project development checklist intended to assist?","doe-microgrid-checklist",["federal agencies"]),
 ("How many phases are in FEMP's distributed energy project process?","doe-project-process",["six"]),
 ("What is Phase 4 of the federal distributed energy project process?","doe-project-process",["Procurement"]),
 ("What modes can a microgrid operate in?","doe-microgrid-systems",["grid-connected","islanded"]),
 ("How does DOE define a microgrid system?","doe-microgrid-systems",["interconnected loads","controllable entity"]),
]
qs=[Question(id=f"public-{i}",query=q,relevant=[d],answer_terms=t,category="public_reference",split="external") for i,(q,d,t) in enumerate(samples)]
write_jsonl(DATA/"public/questions.jsonl",qs)
selection=json.loads((ROOT/"reports/selection.json").read_text())
config=Config(**selection["selected"])
index=Index(load_docs(),Encoder(),semantic=config.chunking=="semantic",persist=False)
result=run(index,qs,config,routing=selection["router_enabled"],graph_enabled=selection["graph_enabled"])
save("public",{"scope":"Six manually authored source-grounded diagnostic questions; written after config freeze; not used for tuning",**result})
print(json.dumps(result["summary"]))
