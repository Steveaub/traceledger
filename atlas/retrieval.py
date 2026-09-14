import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
import numpy as np
import networkx as nx
from fastembed import TextEmbedding
from fastembed.rerank.cross_encoder import TextCrossEncoder
from rank_bm25 import BM25Okapi
from atlas.corpus import ROOT, DATA
from atlas.schema import Chunk


def tokens(text):
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower())


def sentences(text):
    return [(m.start(),m.end(),m.group().strip()) for m in re.finditer(r"[^.!?\n]+(?:[.!?]|$)",text) if m.group().strip()]


class Encoder:
    def __init__(self):
        self.model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2", threads=2, providers=["CPUExecutionProvider"], specific_model_path=str(ROOT/"models/embedding"), local_files_only=True)
        self.cache = {}

    def encode(self, texts):
        missing = list(dict.fromkeys(t for t in texts if t not in self.cache))
        if missing:
            for t, v in zip(missing,self.model.embed(missing,batch_size=32)):
                self.cache[t] = np.asarray(v,dtype=np.float32)
        result=np.stack([self.cache[t] for t in texts])
        # Bound long-running server memory; indexing batches remain deterministic.
        if len(self.cache)>4096:
            self.cache.clear()
        return result


@dataclass(frozen=True)
class Config:
    name: str = "baseline"
    chunking: str = "fixed"
    hybrid: bool = False
    expansion: bool = False
    rerank: bool = False
    graph: bool = False


def chunk_document(doc, encoder, semantic=False):
    spans = []
    if not semantic:
        words = list(re.finditer(r"\S+",doc.text))
        for i in range(0,len(words),80):
            end = min(i+100,len(words))
            spans.append((words[i].start(), words[end-1].end()))
            if end == len(words):
                break
    else:
        sents = sentences(doc.text)
        if not sents:
            sents = [(0,len(doc.text),doc.text)]
        emb = encoder.encode([x[2] for x in sents])
        start, count = sents[0][0],0
        for i,(a,b,s) in enumerate(sents):
            n = len(tokens(s))
            boundary = i>0 and (count+n>100 or (count>=25 and float(emb[i]@emb[i-1])<0.45))
            if boundary:
                spans.append((start,sents[i-1][1]))
                start,count = a,0
            count += n
        spans.append((start,sents[-1][1]))
    # Guard very long sentences and preserve exact source offsets.
    bounded = []
    for a,b in spans:
        ws = list(re.finditer(r"\S+",doc.text[a:b]))
        for i in range(0,len(ws),100):
            bounded.append((a+ws[i].start(),a+ws[min(i+100,len(ws))-1].end()))
    return [Chunk(id=f"{doc.id}:{i}",doc_id=doc.id,text=doc.text[a:b],start=a,end=b) for i,(a,b) in enumerate(bounded)]


class Index:
    def __init__(self, docs, encoder, semantic=False, persist=True):
        t = time.perf_counter()
        self.docs = {d.id:d for d in docs}
        if len(self.docs)!=len(docs):
            raise ValueError("Duplicate document IDs")
        self.encoder = encoder
        self.fingerprint = hashlib.sha256(json.dumps([d.model_dump() for d in docs],sort_keys=True).encode()).hexdigest()
        self.chunks = [c for d in docs if d.current for c in chunk_document(d,encoder,semantic)]
        self.vectors = encoder.encode([c.text for c in self.chunks])
        self.bm25 = BM25Okapi([tokens(c.text) for c in self.chunks])
        self.graph = nx.MultiGraph()
        for d in docs:
            if not d.current:
                continue
            for edge in d.edges:
                if edge.evidence not in d.text:
                    raise ValueError(f"Ungrounded graph edge in {d.id}")
                self.graph.add_edge(edge.source,edge.target,relation=edge.relation,doc_id=d.id,evidence=edge.evidence,
                                    asserted_source=edge.source,asserted_target=edge.target)
        self.reranker = None
        if persist:
            folder = DATA/"index"/("semantic" if semantic else "fixed")
            folder.mkdir(parents=True,exist_ok=True)
            np.save(folder/"vectors.npy",self.vectors,allow_pickle=False)
            (folder/"chunks.json").write_text(json.dumps([c.model_dump() for c in self.chunks]),encoding="utf-8")
            (folder/"manifest.json").write_text(json.dumps({"corpus_sha256":self.fingerprint,"chunks":len(self.chunks),"dimensions":384}),encoding="utf-8")
        self.build_ms = (time.perf_counter()-t)*1000

    def allowed(self, doc_id, projects):
        return projects is None or self.docs[doc_id].project == "public" or self.docs[doc_id].project in projects

    def graph_evidence(self, query, projects, sources=None):
        seeds = [n for n in self.graph if re.search(r"(?<![\w-])"+re.escape(n)+r"(?![\w-])",query,re.I)]
        scores, paths = defaultdict(float), []
        frontier, seen = list(seeds),set(seeds)
        for depth in range(3):
            following=[]
            for node in frontier:
                for _,other,data in self.graph.edges(node,data=True):
                    if not self.allowed(data["doc_id"],projects) or (sources is not None and self.docs[data["doc_id"]].channel not in sources):
                        continue
                    scores[data["doc_id"]] += 1/(depth+1)
                    paths.append({"source":data["asserted_source"],"target":data["asserted_target"],
                                  "traversed_from":node,"traversed_to":other,"depth":depth+1,**data})
                    if other not in seen:
                        following.append(other)
                        seen.add(other)
            frontier=following
        return scores,paths

    def search(self, query, config, k=5, projects=None, sources=None):
        t=time.perf_counter()
        rewritten = re.sub(r"\b(?:please|could you|can you)\b", "",query,flags=re.I).strip()
        if config.expansion:
            aliases = {"fall behind":"delay commissioning", "purchase order":"procurement lesson", "move the milestone":"decision schedule delay", "linked":"relationship addresses modifies", "equipment":"equipment model vendor"}
            rewritten += " " + " ".join(v for key,v in aliases.items() if key in query.lower())
        else:
            rewritten=query
        qvec=self.encoder.encode([rewritten])[0]
        scores=self.vectors@qvec
        allowed=[i for i,c in enumerate(self.chunks) if self.allowed(c.doc_id,projects) and (sources is None or self.docs[c.doc_id].channel in sources)]
        dense=sorted(allowed,key=lambda i:float(scores[i]),reverse=True)
        combined={i:float(scores[i]) for i in dense}
        path="vector"
        if config.hybrid:
            lexical=self.bm25.get_scores(tokens(rewritten))
            bm=sorted(allowed,key=lambda i:float(lexical[i]),reverse=True)
            combined=defaultdict(float)
            for ranking in [dense,bm]:
                for rank,i in enumerate(ranking[:40]):
                    combined[i]+=1/(60+rank+1)
            path="hybrid"
        graph_paths=[]
        if config.graph:
            gs,graph_paths=self.graph_evidence(query,projects,sources)
            if gs:
                # Rank provenance-bearing graph evidence before semantic fillers.
                ranking=sorted(gs,key=lambda d:gs[d],reverse=True)
                for rank,did in enumerate(ranking):
                    candidates=[i for i in allowed if self.chunks[i].doc_id==did]
                    if candidates:
                        i=max(candidates,key=lambda j:float(scores[j]))
                        combined[i]=combined.get(i,0)+2/(rank+1)
                path="graph+"+path
        candidates=sorted(combined,key=lambda i:combined[i],reverse=True)[:20]
        if config.rerank and candidates:
            if self.reranker is None:
                self.reranker=TextCrossEncoder("Xenova/ms-marco-MiniLM-L-6-v2",threads=2,providers=["CPUExecutionProvider"],specific_model_path=str(ROOT/"models/reranker"),local_files_only=True)
            rs=list(self.reranker.rerank(query,[self.chunks[i].text for i in candidates],batch_size=16))
            candidates=[i for _,i in sorted(zip(rs,candidates),reverse=True)]
        hits, seen=[],set()
        for i in candidates:
            c=self.chunks[i]
            if c.doc_id in seen:
                continue
            seen.add(c.doc_id)
            d=self.docs[c.doc_id]
            hits.append({"chunk_id":c.id,"doc_id":c.doc_id,"title":d.title,"text":c.text,"start":c.start,"end":c.end,"source":d.source,"synthetic":d.synthetic,"dense_score":float(scores[i]),"score":float(combined[i])})
            if len(hits)>=k:
                break
        return {"hits":hits,"path":path,"rewritten_query":rewritten,"graph_paths":graph_paths,"retrieval_ms":(time.perf_counter()-t)*1000}


def route(query, selected, graph_enabled):
    relation = bool(re.search(r"\b(trace|linked|affected|same equipment|change impact)\b",query,re.I))
    if graph_enabled and relation:
        return Config("router-graph",selected.chunking,hybrid=True,graph=True)
    if re.search(r"\b[A-Z]+-\d+\b",query):
        return Config("router-hybrid",selected.chunking,hybrid=True)
    return selected
