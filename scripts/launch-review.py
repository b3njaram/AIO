#!/usr/bin/env python3
"""Private commercial readiness review; never approve, publish or modify a release."""
import argparse,datetime as dt,json,os,re,sys
from pathlib import Path
GATES={'hardware':'Exact hardware and actual installer boot, power/load/thermal and recovery qualification','private_access':'Customer-controlled HTTPS and ACL tests from a second device','security':'Exact release vulnerability remediation and reviewed residual risks','licensing':'Exact-version licenses, notices, corresponding source and branding obligations','sales_us':'Applicable US/Texas registration, tax, receipts and warranty review','sales_mx':'Applicable Mexico/Chihuahua registration, tax, receipts and consumer warranty review','agreements':'Reviewed customer agreements, returns, support scope and privacy disclosures','handoff':'Actual customer setup, backup recovery training and acceptance'}
def template(sha):
    if not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('Full release SHA required')
    return {'schema':1,'commit':sha,'markets':['US','MX'],'gates':{k:{'state':'pending','reference':'','reviewed_at':''} for k in GATES}}
def review(sha,evidence,ci):
    expected=template(sha)
    if evidence.get('schema')!=1 or evidence.get('commit')!=sha or set(evidence.get('gates',{}))!=set(GATES):raise ValueError('Evidence must refer to exact release and all gates')
    markets=evidence.get('markets')
    if not isinstance(markets,list) or not markets or len(set(markets))!=len(markets) or set(markets)-{'US','MX'}:raise ValueError('Choose actual markets')
    result={}
    for k,item in evidence['gates'].items():
        if set(item)!={'state','reference','reviewed_at'} or item['state'] not in ('pending','failed','reviewed','deferred'):raise ValueError('Invalid manual evidence state')
        required=not (k=='sales_us' and 'US' not in markets or k=='sales_mx' and 'MX' not in markets)
        complete=False
        if item['state']=='reviewed':
            stamp=dt.datetime.fromisoformat(item['reviewed_at'])
            if not stamp.tzinfo or stamp>dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=2) or not isinstance(item['reference'],str) or not item['reference'].strip() or len(item['reference'])>500:raise ValueError('Reviewed item requires actual dated evidence reference')
            complete=True
        result[k]={'required':required,'state':item['state'],'documented':complete}
    # A supplied report is not automatically trusted as a fresh CI API response.
    software=ci.get('commit')==sha and ci.get('software_gates_passed') is True
    return {'commit':sha,'markets':markets,'software_report_passed':software,'manual_gates':result,'all_documented':software and all(not x['required'] or x['documented'] for x in result.values()),'commercial_release_approved':False,'note':'Operator evidence review only. Independently verify current CI, evidence and legal obligations. No commercial approval is issued.'}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('commit');p.add_argument('--template',type=Path);p.add_argument('--evidence',type=Path);p.add_argument('--ci-report',type=Path);a=p.parse_args()
    if a.template:
        if a.evidence or a.ci_report:p.error('Choose template or review')
        out=a.template.expanduser().absolute();root=Path(__file__).resolve().parents[1]
        if out.parent.resolve()==root or root in out.parent.resolve().parents:p.error('Keep evidence outside Git')
        os.umask(0o077)
        with out.open('x') as f:json.dump(template(a.commit),f,indent=2)
        print('Private blank checklist created. No gates marked reviewed.');return 0
    if not a.evidence or not a.ci_report:p.error('Provide evidence and exact revision readiness report')
    result=review(a.commit,json.loads(a.evidence.read_text()),json.loads(a.ci_report.read_text()))
    print(json.dumps(result,indent=2))
    return not result['all_documented']
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit('Launch review refused: '+type(e).__name__)
