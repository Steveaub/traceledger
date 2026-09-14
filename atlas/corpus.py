"""Deterministic fictional universe. Eval labels never enter the runtime index."""
import json
from pathlib import Path
from atlas.schema import Document, Question

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r.model_dump() if hasattr(r, "model_dump") else r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")


def load_docs():
    paths = [DATA / "synthetic/documents.jsonl", DATA / "public/documents.jsonl", DATA / "conversations/documents.jsonl"] + sorted((DATA / "ingested").glob("*.jsonl"))
    return [Document.model_validate_json(line) for p in paths if p.exists() for line in p.read_text(encoding="utf-8").splitlines() if line]


def load_questions(path=None):
    path = path or DATA / "synthetic/questions.jsonl"
    return [Question.model_validate_json(s) for s in path.read_text(encoding="utf-8").splitlines() if s]


def generate():
    docs, questions, universe = [], [], []
    names = ["Alpha", "Beta", "Cedar", "Delta", "Elm", "Falcon", "Granite", "Harbor", "Iris", "Juniper", "Kestrel", "Laurel"]
    vendors = ["Northstar Power", "Meridian Controls", "Summit Electric", "Tidal Systems"]
    causes = ["transformer winding insulation failed factory testing", "controller firmware dropped synchronization messages", "cooling pump seals leaked during endurance testing", "switchgear relay settings conflicted with the utility study"]
    mitigations = ["require witnessed factory acceptance before shipment", "validate firmware interoperability in a hardware-in-the-loop test", "inspect replacement seals and repeat the endurance test", "complete an independent protection coordination review"]
    equipment = ["TX-880", "CTRL-420", "PUMP-310", "SWG-610"]
    for i, name in enumerate(names):
        project, site = f"PRJ-{i+1:03}", f"SITE-{i+1:03}"
        model, vendor = equipment[i % 4], vendors[i % 4]
        inc, risk, change, lesson, decision, milestone, requirement = [f"{x}-{i+1:03}" for x in ["INC", "RISK", "CR", "LL", "DEC", "MS", "REQ"]]
        cause, mitigation = causes[i % 4], mitigations[i % 4]
        delay = [6, 3, 4, 2][i % 4] + i // 4
        split = "dev" if i < 6 else "test"
        status = "closed" if i < 4 else "active"
        universe.append(dict(id=project, name=name, site=site, equipment=model, vendor=vendor, status=status, delay_weeks=delay))

        def add(kind, body, edges=(), current=True):
            did = f"{project}-{kind}"
            docs.append(Document(id=did, title=f"{name} / {kind.replace('_', ' ')}", text=body, project=project, kind=kind, source=f"synthetic:{did}", synthetic=True, current=current, date="2026-06-01" if current else "2026-02-01", edges=[dict(source=a, relation=b, target=c, evidence=e) for a,b,c,e in edges]))
            return did

        charter = f"Project {name} ({project}) is {status}. {project} serves {site}. {project} uses {model}. {vendor} supplies {model}."
        add("charter", charter + f"\n\nScope: deliver a resilient microgrid for municipal facilities. The sponsor requires documented acceptance and a handover package. The project manager coordinates procurement, safety review, construction and commissioning.\n\nGate reviews require current risks, verified technical assumptions and explicit decision owners.", [(project,"located_at",site,f"{project} serves {site}."),(project,"uses",model,f"{project} uses {model}."),(vendor,"supplies",model,f"{vendor} supplies {model}.")])
        incident = f"Incident {inc} on Project {name}: {cause}. {inc} affected {model}. The commissioning milestone slipped by {delay} weeks. Containment: quarantine the affected unit pending vendor review."
        add("incident", incident + "\n\nThe site team recorded photographs, instrument readings and the inspection checklist. This record describes a fictional event; it is not an equipment operating procedure.", [(inc,"affected",model,f"{inc} affected {model}."),(inc,"delayed",milestone,f"The commissioning milestone slipped by {delay} weeks.")])
        risktext = f"Risk {risk} for Project {name}: repeat {model} acceptance failure could delay energization. Owner: procurement lead. {risk} threatens {milestone}. Trigger: missing factory test evidence ten business days before shipment. Response: {mitigation}."
        add("risk",risktext,[(risk,"threatens",milestone,f"{risk} threatens {milestone}."),(risk,"concerns",model,f"repeat {model} acceptance failure could delay energization.")])
        ctext = f"Change {change} on Project {name} revises acceptance requirement {requirement}. {change} modifies {requirement}. Approved scope: {mitigation}. {change} addresses {inc}. Approval owner: engineering review board. Budget delta: {15000+i*2500} fictional USD."
        add("change",ctext,[(change,"modifies",requirement,f"{change} modifies {requirement}."),(change,"addresses",inc,f"{change} addresses {inc}.")])
        ltext = f"Lesson {lesson} from Project {name}: {mitigation}. {lesson} follows {inc}. {lesson} applies to {model}. Reuse this lesson at the procurement gate of future projects before purchase-order release."
        add("lesson",ltext,[(lesson,"follows",inc,f"{lesson} follows {inc}."),(lesson,"applies_to",model,f"{lesson} applies to {model}.")])
        dtext = f"Decision {decision} moved {milestone} by {delay} weeks because {cause}. {decision} responds to {inc}. The board accepted the schedule change only after reviewing the incident and change {change}."
        add("decision",dtext,[(decision,"responds_to",inc,f"{decision} responds to {inc}."),(decision,"moves",milestone,f"Decision {decision} moved {milestone} by {delay} weeks because {cause}.")])
        add("status",f"Current Project {name} status: commissioning is delayed {delay} weeks. The approved recovery plan tracks {change}, {risk} and {milestone}. Technical cause: {cause}. Next action: {mitigation}.")
        add("status_old",f"Preliminary Project {name} forecast: commissioning is on time. The vendor expects to ship next month. This forecast predates {inc} and has been superseded by the current status report.",current=False)
        add("rfi",f"RFI for Project {name}: please confirm the test evidence required for {model}. Engineering references change {change}. The supplier must return signed acceptance records with the shipping release.")
        add("minutes",f"Project {name} coordination meeting: the team reviewed civil works and cable routing. Procurement will chase the {model} documentation. No new engineering acceptance decision was authorized in this meeting.")
        add("vendor",f"{vendor} correspondence for Project {name}: replacement materials are reserved. Factory test witnessing remains subject to review under {change}. The commercial contact cannot waive engineering requirements.")
        add("handover",f"Project {name} handover checklist: archive drawings, training records, test certificates and lessons learned. Resolve outstanding change requests and name an operations owner before final acceptance.")
        # Distractors are deliberately related, not random text.
        for j in range(3):
            add(f"routine_{j}",f"Project {name} week {j+1} coordination log: site access, fencing and document control are progressing. Vendor {vendor} joined the meeting. There were no changes to the commissioning baseline in this routine log. Equipment tags and inspection forms remain under document control.")

        def q(category, query, relevant, terms):
            questions.append(Question(id=f"{project}-{category}",query=query,relevant=[f"{project}-{r}" for r in relevant],answer_terms=terms,category=category,split=split))
        q("direct",f"Which equipment and vendor does Project {name} use?",["charter"],[model,vendor])
        q("semantic",f"What caused Project {name} to fall behind its commissioning schedule?",["incident","decision","status"],[cause,str(delay)])
        q("exact",f"What requirement does {change} modify?",["change"],[requirement])
        q("lesson",f"What should we learn from Project {name} before releasing a purchase order?",["lesson"],[mitigation])
        q("decision",f"Why did {decision} move the milestone?",["decision","incident"],[cause])
        q("risk",f"What triggers {risk} and what response is planned?",["risk"],["ten business days",mitigation])
        q("conflict",f"What is the current commissioning delay for Project {name}?",["status"],[f"{delay} weeks"])
        q("change_impact",f"Trace the requirement and incident linked to {change}.",["change","incident"],[requirement,inc])
        related = [f"PRJ-{n+1:03}-charter" for n in range(4,12) if n%4 == i%4]
        questions.append(Question(id=f"{project}-multi_hop",query=f"Which active projects use the equipment affected by {inc}, and what lesson follows that incident?",relevant=[f"{project}-incident",f"{project}-lesson"]+related,answer_terms=[model,mitigation]+[names[n] for n in range(4,12) if n%4==i%4],category="multi_hop",split=split))
    for n, query in enumerate(["What is the CEO's private bank password?", "What is the weather forecast for Mars?", "Who won the 2050 baseball championship?", "What did Project Omega spend on helicopter repairs?", "What is the secret access token for the grid controller?", "What is the final approved contract value of Project Alpha?"]):
        questions.append(Question(id=f"absent-{n}",query=query,relevant=[],category="unanswerable",split="dev" if n<3 else "test"))
    write_jsonl(DATA/"synthetic/documents.jsonl",docs)
    write_jsonl(DATA/"synthetic/questions.jsonl",questions)
    (DATA/"synthetic/universe.json").write_text(json.dumps(universe,indent=2),encoding="utf-8")
    print(f"Generated {len(docs)} fictional records, {len(questions)} questions")


if __name__ == "__main__":
    generate()
