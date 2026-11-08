"""Opt-in real API verification on fictional fixtures; results stay in ignored var/."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from service import DocumentBot

def main():
    service=DocumentBot()
    owner='cli:vpg07-verification'
    rows=[]
    target=Path('var/live-results.json');target.parent.mkdir(exist_ok=True)
    def record(name,result):
        rows.append({'check':name,'result':result})
        target.write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        print(name,json.dumps(result,ensure_ascii=False),flush=True)
    if '--resume' in sys.argv and target.exists():
        rows.extend(json.loads(target.read_text()))
    else:
        for path in ['examples/service-policy.md','examples/service.docx','examples/policy.pdf','examples/scanned-policy.pdf']:
            record('ingest:'+path,service.ingest(owner,path))
    before=len(service.documents.rows(owner))
    service.ingest(owner,'examples/service-policy.md')
    after=len(service.documents.rows(owner))
    record('duplicate',{'before':before,'after':after,'same_count':before==after})
    questions=['Сколько стоит тариф Орбита и за сколько дней обрабатывается заявка?',
               'Сколько стоит Aurora и сколько занимает onboarding?',
               'Какой срок гарантии на оборудование?',
               'Какой секретный тестовый код указан в отсканированной инструкции?',
               'Какой адрес склада указан в документах?']
    for q in questions:
        r=service.handle(owner,q)
        record(q,{'answer':r['answer'],'sources':r['sources'],'calls':r['calls']})
    record('isolation',{'other_owner_documents':len(service.documents.rows('cli:vpg07-other-user'))})
    for q in ['Расскажи случайный факт о кошках.','Какая сейчас погода в Москве?','Покажи случайную собаку и проанализируй фото.']:
        r=service.handle(owner,q)
        record(q,{'answer':r['answer'],'calls':r['calls'],'photos':len(r['attachments']),'tool_results':r['tool_results']})
if __name__=='__main__':main()
