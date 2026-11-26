"""Read-only block topology and conservative Linux md RAID1 planning."""
import json,os,re,stat,subprocess
from pathlib import Path
def command(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=30)
def topology():
    raw=json.loads(command('lsblk','--json','--bytes','--paths','--output','NAME,KNAME,TYPE,SIZE,FSTYPE,MOUNTPOINTS,PKNAME,RO,MODEL,WWN,SERIAL'))
    nodes={}
    def walk(rows,parent=None):
        for row in rows:
            key=row['kname'];entry=nodes.setdefault(key,{k:v for k,v in row.items() if k!='children'})
            entry.setdefault('parents',set());entry.setdefault('children',set())
            if parent:
                entry['parents'].add(parent);nodes[parent]['children'].add(key)
            walk(row.get('children',[]),key)
    walk(raw['blockdevices'])
    return nodes
def source_for(path):
    # major:minor identifies the mounted block device even when its source is an alias.
    value=command('findmnt','-n','-o','MAJ:MIN','--target',str(path)).strip()
    if not re.fullmatch(r'\d+:\d+',value):raise ValueError('Unsupported mounted filesystem')
    return '/dev/'+Path('/sys/dev/block',value).resolve(strict=True).name
def read_md(device,sysroot=Path('/sys/class/block')):
    root=sysroot/Path(device).name/'md'
    def read(name):return (root/name).read_text().strip()
    level=read('level');count=int(read('raid_disks'));degraded=int(read('degraded'));action=read('sync_action')
    members=[]
    for p in sorted(root.glob('dev-*')):
        state=(p/'state').read_text().strip().split(',')
        block=(p/'block').resolve(strict=True)
        members.append({'device':'/dev/'+block.name,'state':state,'slot':(p/'slot').read_text().strip()})
    return {'level':level,'expected':count,'degraded':degraded,'sync_action':action,'array_state':read('array_state'),'component_bytes':int(read('component_size'))*512,'members':members}
def ancestry(nodes,key):
    result=set()
    def visit(k):
        if k in result:return
        result.add(k)
        for p in nodes.get(k,{}).get('parents',[]):visit(p)
    visit(key);return result
def blank_disk(nodes,alias,protected=()):
    p=Path(alias)
    if not re.fullmatch(r'/dev/disk/by-id/[A-Za-z0-9_.:+-]+',str(p)) or not p.is_symlink():raise ValueError('Use an existing stable whole-disk /dev/disk/by-id alias')
    key=str(p.resolve(strict=True));d=nodes.get(key)
    if not d or d['type']!='disk' or d.get('ro') or d.get('children') or d.get('fstype') or any(d.get('mountpoints') or []) or d.get('parents') or key in protected:
        raise ValueError('Disk is not an unused writable whole disk')
    if not stat.S_ISBLK(Path(key).stat().st_mode):raise ValueError('Not a block device')
    if any((Path('/sys/class/block')/Path(key).name/'holders').iterdir()):raise ValueError('Disk has active holders')
    signatures=json.loads(command('wipefs','--no-act','--json',key)).get('signatures')
    if signatures!=[]:raise ValueError('Disk contains signatures or could not be verified blank; no wiping is provided')
    if not (d.get('wwn') or d.get('serial')):raise ValueError('Stable hardware identifier unavailable')
    return d
def replacement(md,disk):
    if md['level']!='raid1' or md['expected']!=2 or md['degraded']!=1 or md['sync_action']!='idle' or md['array_state'] not in ('active','clean','active-idle'):
        raise ValueError('Only idle two-member RAID1 with exactly one missing member is supported')
    if len(md['members'])!=1 or 'in_sync' not in md['members'][0]['state']:raise ValueError('Remove the failed member manually after positively identifying it; require one healthy surviving member')
    if disk['size']<md['component_bytes']:raise ValueError('Replacement too small')
def expansion(md,nodes,fstype):
    if md['level']!='raid1' or md['expected']!=2 or md['degraded']!=0 or md['sync_action']!='idle' or len(md['members'])!=2 or any('in_sync' not in x['state'] for x in md['members']):
        raise ValueError('Require an idle fully synchronized two-member RAID1')
    if fstype!='ext4':raise ValueError('Only direct ext4 on RAID1 expansion is supported')
    sizes=[nodes[x['device']]['size'] for x in md['members']]
    if min(sizes)<=md['component_bytes']+16*1024**2:raise ValueError('Both members must have meaningful additional capacity')
    return min(sizes)
def snapshot(instance):
    try:
        nodes=topology();source=source_for(instance);d=nodes[source]
        md=read_md(source) if d['type']=='raid1' else None
        fs=os.statvfs(instance)
        return {'filesystem':d.get('fstype') or 'unknown','total_bytes':fs.f_blocks*fs.f_frsize,'free_bytes':fs.f_bavail*fs.f_frsize,'redundancy':{'level':md['level'],'state':'degraded' if md['degraded'] else ('syncing' if md['sync_action']!='idle' else 'healthy' if md['array_state'] in ('active','clean','active-idle','readonly','read-auto') else 'review'),'expected':md['expected'],'missing':md['degraded'],'sync_action':md['sync_action']} if md else {'level':'unverified','state':'unknown'}}
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError):return {'redundancy':{'level':'unverified','state':'unknown'}}
