"""Create fictional message fixtures and separate investigation evaluation labels."""
import json
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from atlas.corpus import DATA, write_jsonl
from atlas.schema import Document, Question


def build():
    originals = {d.id: d for d in [Document.model_validate_json(x) for x in
        (DATA/'synthetic/documents.jsonl').read_text(encoding='utf-8').splitlines()]}
    messages, questions = [], []
    for i in range(1, 13):
        project = f'PRJ-{i:03}'
        name = originals[project+'-charter'].title.split(' / ')[0]
        incident = originals[project+'-incident'].text.split('\n')[0]
        weeks = re.search(r'slipped by (\d+) weeks', incident)[1]
        owner = f'{name} engineering review board'
        change, decision = f'CR-{i:03}', f'DEC-{i:03}'
        fixtures = [
            ('email-proposal', 'email', 'Vendor coordinator', 'proposed', '2026-05-12T09:00:00Z',
             f'Project {name}: proposal for {change}: reduce the commissioning delay to one week. This is a vendor suggestion, not an approved schedule change.'),
            ('email-approval', 'email', owner, 'approved', '2026-05-14T14:00:00Z',
             f'Project {name}: {owner} approved {change} under {decision}. The approved commissioning delay remains {weeks} weeks. The one-week vendor proposal was rejected. This approval does not authorize waiving acceptance tests.'),
            ('slack-cause', 'slack', 'Site engineer', 'recorded', '2026-05-12T10:00:00Z', incident),
            ('slack-followup', 'slack', 'Project coordinator', 'unspecified', '2026-05-13T11:00:00Z',
             f'Project {name}: has {change} been approved? Please check the engineering board email and the schedule register before calling the recovery date final.'),
            ('teams-schedule', 'teams', 'Schedule controller', 'recorded', '2026-05-15T16:00:00Z',
             f'Project {name}: schedule register updated after {decision}. The commissioning baseline now records the approved {weeks}-week delay for {change}. The superseded one-week draft is not the baseline.'),
            ('teams-open', 'teams', 'Procurement lead', 'unspecified', '2026-05-15T16:30:00Z',
             f'Project {name}: final vendor compensation for {change} is unresolved. No signed settlement or final approved compensation amount is present in this thread.')]
        for suffix, channel, author, status, date, text in fixtures:
            did = project+'-'+suffix
            messages.append(Document(id=did, title=f'{name} / {channel} / {suffix.split("-",1)[1]}',
                text=text, source='synthetic:'+did, project=project, kind='conversation', synthetic=True,
                date=date, channel=channel, author=author, decision_status=status,
                thread_id=f'{project}-{channel}-recovery'))
        questions.append(Question(id=project+'-investigation',
            query=f'Investigate Project {name}: why was commissioning delayed, who approved the change, and was the schedule updated?',
            relevant=[project+'-incident', project+'-slack-cause', project+'-email-approval', project+'-teams-schedule', project+'-decision', project+'-status', project+'-change'],
            answer_terms=[owner, 'schedule register updated', f'{weeks} weeks'],
            category='decision_trace', split='dev' if i<=6 else 'test'))
    questions += [Question(id='missing-incident', query='Investigate INC-999 and who approved its change.',relevant=[],category='missing',split='test'),
                  Question(id='missing-project',query='Investigate Project Omega and its approval.',relevant=[],category='missing',split='dev')]
    write_jsonl(DATA/'conversations/documents.jsonl',messages)
    write_jsonl(DATA/'conversations/questions.jsonl',questions)
    print(f'Created {len(messages)} fictional messages and {len(questions)} separate investigation cases.')


if __name__ == '__main__':
    build()
