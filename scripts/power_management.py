"""Local NUT monitoring; never issue a UPS command or shutdown."""
import math,re,subprocess
from pathlib import Path
def parse(text):
    fields=dict(x.split(': ',1) for x in text.splitlines() if ': ' in x)
    codes=set(fields.get('ups.status','').split())
    state='unknown' if not codes else 'low_battery' if codes&{'LB','FSD'} else 'on_battery' if 'OB' in codes else 'online' if 'OL' in codes and 'OFF' not in codes else 'review'
    result={'state':state}
    for source,dest,maximum in [('battery.charge','charge_percent',100),('battery.runtime','runtime_seconds',604800),('ups.load','load_percent',100)]:
        try:
            value=float(fields[source])
            if math.isfinite(value) and 0<=value<=maximum:result[dest]=round(value,1)
        except (KeyError,ValueError):pass
    return result
def snapshot(instance):
    path=Path(instance)/'.ups-name'
    try:
        if path.is_symlink() or path.stat().st_size>128:return {'state':'unknown'}
        name=path.read_text().strip()
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,48}',name):return {'state':'unknown'}
        data=subprocess.check_output(['upsc',name+'@127.0.0.1'],text=True,stderr=subprocess.DEVNULL,timeout=5)
        result=parse(data)
        result['monitor_active']=subprocess.run(['systemctl','is-active','--quiet','nut-monitor.service'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5).returncode==0
        return result
    except FileNotFoundError:return {'state':'not_configured' if not path.exists() else 'unknown'}
    except (OSError,ValueError,subprocess.SubprocessError):return {'state':'unknown'}
