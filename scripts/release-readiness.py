#!/usr/bin/env python3
"""Read exact-revision GitHub Actions evidence. Never create tags or certify hardware."""
import argparse,json,os,re,sys,urllib.request,urllib.parse
from datetime import datetime,timezone
REPO='b3njaram/AIO'
GATES={
    'check.yml':('static',),
    'pilot.yml':('isolation','full-stack','media-recovery','library-recovery','office-recovery','infrastructure-recovery','staged-upgrade'),
    'browser.yml':('browser','docker-preview'),
    'appliance-iso.yml':('iso',),
    'appliance-vm.yml':('vm',),
    'storage-raid.yml':('raid',),
    'release-security.yml':('image-scan',)}
def api(path):
    token=os.environ.get('GITHUB_TOKEN')
    headers={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28','User-Agent':'Jobbi-release-readiness'}
    if token:headers['Authorization']='Bearer '+token
    req=urllib.request.Request('https://api.github.com/repos/'+REPO+path,headers=headers)
    # Do not follow redirects to another host with authentication headers.
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self,*args,**kwargs):raise ValueError('Unexpected GitHub API redirect')
    with urllib.request.build_opener(NoRedirect()).open(req,timeout=20) as r:return json.load(r)
def evaluate(sha,fetch=api):
    if not re.fullmatch('[0-9a-f]{40}',sha):raise ValueError('Exact full release commit required')
    results=[]
    for workflow,required in GATES.items():
        runs=fetch('/actions/workflows/'+workflow+'/runs?head_sha='+sha+'&per_page=100')['workflow_runs']
        # PR jobs may run on a synthetic merge and skip expensive checks.
        # Only push or explicit dispatch at this exact commit can satisfy a gate.
        eligible=[r for r in runs if r['head_sha']==sha and r['event'] in ('push','workflow_dispatch')]
        best=None
        for r in sorted(eligible,key=lambda r:r['id'],reverse=True):
            jobs=fetch('/actions/runs/'+str(r['id'])+'/jobs?filter=latest&per_page=100')['jobs']
            byname={j['name']:j for j in jobs}
            states={name:('missing' if name not in byname else byname[name]['conclusion'] or byname[name]['status']) for name in required}
            candidate={'workflow':workflow,'run':r['id'],'states':states,'pass':r['status']=='completed' and r['conclusion']=='success' and all(v=='success' for v in states.values())}
            # Ignore entirely skipped/manual opt-out runs, but do not hide a
            # more recent real failure or in-progress execution behind older success.
            if all(v in ('missing','skipped') for v in states.values()):
                if best is None:best=candidate
                continue
            best=candidate;break
        results.append(best or {'workflow':workflow,'run':None,'states':{x:'missing' for x in required},'pass':False})
    return {'schema':1,'commit':sha,'checked_at':datetime.now(timezone.utc).isoformat(),'software_gates_passed':all(x['pass'] for x in results),'gates':results,'manual_release_gates':['Actual Ubuntu installer boot and physical appliance qualification','Customer-owned tailnet HTTPS and ACL denial from another device','Real load, power, thermals, SMART, backup restore and restart','Exact-version licensing and distribution obligations','Commercial agreements, tax, receipts and warranty compliance'],'commercial_release_approved':False}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('commit');a=p.parse_args()
    result=evaluate(a.commit)
    print(json.dumps(result,indent=2))
    return not result['software_gates_passed']
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit('Release evidence unavailable: '+type(e).__name__)
