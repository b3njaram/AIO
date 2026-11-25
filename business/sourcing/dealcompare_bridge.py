"""Use the pinned DealCompare checkout, including its cached API results and variation screening."""
import os, subprocess, sys
from pathlib import Path
PIN='7cf8b54f13eac82816e3363363ed7ae43e84dc28'
def load_env(path):
    p=Path(path).expanduser()
    if not p.exists(): return
    if p.stat().st_mode & 0o077: raise ValueError('Credentials file must be private: chmod 600')
    for line in p.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):continue
        k,sep,v=line.partition('=')
        if sep and k.strip() in ('EBAY_CLIENT_ID','EBAY_CLIENT_SECRET'):
            os.environ.setdefault(k.strip(),v.strip().strip('"').strip("'"))
def connect(path):
    root=Path(path).expanduser().resolve()
    if not (root/'search_engine.py').is_file(): raise ValueError('Run setup-dealcompare.sh first')
    head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if head!=PIN: raise ValueError('DealCompare checkout must match pinned revision; run setup-dealcompare.sh')
    if subprocess.check_output(['git','-C',str(root),'status','--porcelain','--untracked-files=no'],text=True).strip(): raise ValueError('Modified DealCompare checkout; refusing to execute')
    sys.path.insert(0,str(root))
    import ebay_api
    import search_engine
    return ebay_api,search_engine
def search(engine,api,part,allow_html=False):
    state=api.credential_state()
    if state!='configured' and not (state=='missing' and allow_html):
        return [],['eBay API credentials '+state+'; no HTML request sent']
    queries=part.get('models') or [part['query']]
    rows=[];warnings=[]
    for query in queries:
        items,notes=engine.search_ebay(query,1500 if part['kind']=='drive' else 2500,pages=1,both_ends=False,use_cache=True)
        rows.extend(items);warnings.extend(notes)
        if any('rate limit' in n.lower() or 'denied access' in n.lower() or 'paused' in n.lower() or 'challenge' in n.lower() for n in notes):break
    return rows,warnings
