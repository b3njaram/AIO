#!/usr/bin/env python3
"""Technician recovery catalog, verified restore and supervised offline update trial."""
import argparse,datetime as dt,fcntl,json,os,re,shlex,subprocess,sys,time
from pathlib import Path
from backup_mount import mount_identity
from restore import verified_archives,metadata
ROOT=Path(__file__).resolve().parents[1]
def run(*cmd,**kw):return subprocess.run(cmd,check=True,**kw)
def ctl(i,*args):return ['bash',str(ROOT/'scripts/ctl.sh'),str(i),*args]
def env(i):
    e=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if e.get('INSTANCE_DIR')!=str(i) or not re.fullmatch(r'jobbi-[a-z0-9-]+',e.get('COMPOSE_PROJECT_NAME','')) or e.get('BIND_IP')!='127.0.0.1':raise ValueError('Require validated loopback-only customer instance')
    return e
def independent(i,b,expected):
    if not b.is_dir() or i.stat().st_dev==b.stat().st_dev or i in b.parents or b in i.parents or mount_identity(b)!=expected:raise ValueError('Approved independent backup filesystem unavailable')
    docker=Path(subprocess.check_output(['docker','info','--format','{{.DockerRootDir}}'],text=True).strip())
    if docker.stat().st_dev==b.stat().st_dev:raise ValueError('Backup shares Docker filesystem')
def candidates(i,b):
    project=env(i)['COMPOSE_PROJECT_NAME'];pat=re.compile(re.escape(project)+r'-\d{8}T\d{6}Z')
    return sorted((x for x in b.iterdir() if pat.fullmatch(x.name) and x.is_dir() and not x.is_symlink() and (x/'SHA256SUMS').is_file()),reverse=True)
def verified(i,b,name):
    if not isinstance(name,str) or name not in {x.name for x in candidates(i,b)}:raise ValueError('Select an exact completed backup of this instance')
    path=b/name;archives=verified_archives(path);e,_,release=metadata(archives['instance.tar.gz'])
    if e['COMPOSE_PROJECT_NAME']!=env(i)['COMPOSE_PROJECT_NAME'] or e['INSTANCE_DIR']!=str(i):raise ValueError('Backup identity mismatch')
    return path,release
def retention(i,b,keep,days):
    """Preview only; require multiple independently checksum-verified recent copies."""
    if keep<3 or days<30:raise ValueError('Keep at least three backups and thirty days')
    if (i/'.upgrade-hold.json').exists() or (i/'.backup-running-services').exists():raise ValueError('Resolve active backup or upgrade before retention review')
    rows=candidates(i,b)
    cutoff=dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=days)
    result=[]
    protected=set(x.name for x in rows[:keep])
    # Verify the protected recent backups before even proposing older copies.
    if len(protected)<keep:raise ValueError('Not enough completed backup generations')
    for name in sorted(protected):verified(i,b,name)
    for x in rows:
        timestamp=dt.datetime.strptime(x.name.rsplit('-',1)[-1],'%Y%m%dT%H%M%SZ').replace(tzinfo=dt.timezone.utc)
        result.append({'name':x.name,'decision':'keep' if x.name in protected or timestamp>=cutoff else 'review_for_manual_retention'})
    return result
def running(i):
    return set(subprocess.check_output(ctl(i,'ps','--status','running','--services'),text=True).split())
def hold(i):
    h=json.loads((i/'.upgrade-hold.json').read_text())
    services=h.get('services')
    if h.get('state')!='held' or not services or len(set(services))!=len(services) or any(not re.fullmatch('[a-z0-9][a-z0-9-]*',s) for s in services):raise ValueError('Invalid source hold journal')
    allowed=set(subprocess.check_output(ctl(i,'config','--services'),text=True).split())
    if not set(services)<=allowed:raise ValueError('Source services changed')
    return h
def related(i,t,h):
    if i==t or i.parent!=t.parent:raise ValueError('Candidate must be a separate sibling instance')
    env(t)
    u=json.loads((t/'upgrade.json').read_text())
    if u.get('source')!=str(i) or u.get('backup')!=h['backup'] or u.get('source_held') is not True or u.get('from')!=json.loads((i/'release.json').read_text())['aio_commit'] or u.get('to')!=json.loads((t/'release.json').read_text())['aio_commit']:raise ValueError('Candidate is not linked to this frozen source')
    return u
def record(i,state):
    tmp=i/'.recovery-state.tmp'
    with tmp.open('x') as out:
        json.dump({'state':state,'at':dt.datetime.now(dt.timezone.utc).isoformat()},out)
        out.flush();os.fsync(out.fileno())
    os.replace(tmp,i/'recovery-state.json')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['catalog','verify','retention','restore','stage','start-trial','rollback']);p.add_argument('instance',type=Path);p.add_argument('backup_root',type=Path);p.add_argument('--mount-id',required=True);p.add_argument('--keep',type=int,default=3);p.add_argument('--days',type=int,default=30);p.add_argument('--backup');p.add_argument('--candidate');p.add_argument('--base-port',type=int);p.add_argument('--to-commit');p.add_argument('--apply',action='store_true');p.add_argument('--confirm-no-candidate-writes',action='store_true',help='Acknowledge trial has no customer writes, or these were separately reconciled');a=p.parse_args()
    i=a.instance.resolve();b=a.backup_root.resolve();e=env(i);independent(i,b,a.mount_id)
    if a.action=='catalog':
        print(json.dumps([{'name':x.name,'completed_manifest':True,'integrity':'not_checked'} for x in candidates(i,b)],indent=2));return
    if a.action=='retention':
        if a.apply:p.error('Retention is preview-only; no automatic deletion')
        print(json.dumps(retention(i,b,a.keep,a.days),indent=2));return
    if a.action=='verify':
        path,release=verified(i,b,a.backup);print('Verified archive checksums and instance identity. Release:',release['aio_commit']);return
    if a.candidate and not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,35}',a.candidate):p.error('Invalid candidate')
    t=i.parent/a.candidate if a.candidate else None
    if a.action in ('stage','restore'):
        if not t or t.exists() or t.is_symlink() or not a.base_port or not 1024<=a.base_port<=65524:p.error('Use a fresh candidate name and unused port range')
    if a.action=='restore':
        path,_=verified(i,b,a.backup)
        cmd=[sys.executable,str(ROOT/'scripts/restore.py'),str(path),'--require-exact-images','--data-root',str(i.parent),'--name',a.candidate,'--base-port',str(a.base_port)]
        print(shlex.join(cmd))
        if a.apply:run(*cmd)
        return
    if a.action=='stage':
        if not a.to_commit or not re.fullmatch('[a-f0-9]{40}',a.to_commit):p.error('Provide an explicitly reviewed full target commit')
        old=json.loads((i/'release.json').read_text())['aio_commit']
        cmd=[sys.executable,str(ROOT/'scripts/stage-upgrade.py'),str(i),str(b),'--from-commit',old,'--to-commit',a.to_commit,'--name',a.candidate,'--base-port',str(a.base_port),'--hold-source']
        run(*cmd)
        if not a.apply:return
        if not sys.stdin.isatty() and os.environ.get('GITHUB_ACTIONS')!='true':p.error('Use a trusted local interactive terminal')
        if (i/'.upgrade-hold.json').exists():p.error('Existing upgrade hold')
        record(i,'preparing')
        try:run(*cmd,'--prepare');record(i,'candidate_ready')
        except (OSError,subprocess.CalledProcessError):
            record(i,'review_required')
            print('Original may remain stopped. Inspect journal and candidate. No automatic deletion or restart.',file=sys.stderr);raise
        return
    h=hold(i);path,_=verified(i,b,Path(h['backup']).name)
    if str(path)!=h['backup']:p.error('Hold archive mismatch')
    if a.action=='start-trial':
        if not t or not t.is_dir():p.error('Specify staged candidate')
        related(i,t,h)
        if running(i) or (i/'.backup-running-services').exists():p.error('Source is not safely held offline')
        if any((t/n).exists() for n in ('.private-serve.json','.upgrade-hold.json')):p.error('Candidate must remain isolated')
        print('Start isolated candidate, not a production cutover. Verify all selected apps with read-only/sample data.')
        if not a.apply:return
        run(*ctl(t,'up','-d','--no-build','--pull','never'))
        for _ in range(36):
            if subprocess.run(['bash',str(ROOT/'scripts/verify.sh'),str(t)]).returncode==0:
                record(i,'trial_reachable');print('Reachability only; functional acceptance still pending.');return
            time.sleep(5)
        record(i,'review_required');raise ValueError('Candidate did not become reachable; original remains held')
    if a.action=='rollback':
        if not t:p.error('Provide candidate name even when staging was interrupted')
        if t.exists():related(i,t,h)
        if not a.confirm_no_candidate_writes:p.error('Confirm no customer writes would be lost or that they have been reconciled')
        print('Stop candidate, restore originally running services, retain both datasets and backup.')
        if not a.apply:return
        if t.exists():
            if (t/'.private-serve.json').exists():p.error('Disable candidate private routes before rollback')
            run(*ctl(t,'stop'))
            if running(t):p.error('Candidate remains running')
        if (i/'.backup-running-services').exists():p.error('Reconcile interrupted backup journal first')
        run(*ctl(i,'start',*h['services']))
        if not set(h['services'])<=running(i):p.error('Original services not all running; hold retained')
        (i/'.upgrade-hold.json').unlink();record(i,'rolled_back')
        print('Original restarted; verify functional acceptance. Candidate and archive retained.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,subprocess.SubprocessError) as e:sys.exit('Recovery operation stopped: '+str(e))
