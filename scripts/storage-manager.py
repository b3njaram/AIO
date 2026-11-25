#!/usr/bin/env python3
"""Technician-only storage plans; no writes to physical disks or md arrays."""
import argparse,json,shlex,sys,subprocess
from pathlib import Path
from storage_manager import topology,source_for,ancestry,read_md,blank_disk,replacement,expansion,snapshot
from restore import verified_archives,metadata
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['status','create-mirror','replace-member','expand-mirror']);p.add_argument('--instance',type=Path);p.add_argument('--backup',type=Path,help='Completed independent backup archive for replacement/expansion');p.add_argument('--disk',action='append',default=[]);a=p.parse_args()
    if a.action=='status':
        if not a.instance:p.error('--instance required')
        print(json.dumps(snapshot(a.instance.resolve()),indent=2));return
    nodes=topology()
    protected=ancestry(nodes,source_for('/'))
    if a.action=='create-mirror':
        if len(a.disk)!=2 or not a.instance is None or a.backup:p.error('Provide exactly two blank disks for a NEW appliance, no instance')
        drives=[blank_disk(nodes,d,protected) for d in a.disk]
        if drives[0]['kname']==drives[1]['kname'] or (drives[0].get('wwn') or drives[0].get('serial'))==(drives[1].get('wwn') or drives[1].get('serial')):p.error('Duplicate physical disk')
        print('NEW RAID1 plan; usable raw capacity at most',min(d['size'] for d in drives),'bytes.')
        print('Confirm both physical drives, backup independence, and unused array name. Only then use the distro mdadm installer or reviewed command:')
        print(shlex.join(['sudo','mdadm','--create','/dev/md/jobbi-data','--metadata=1.2','--level=1','--raid-devices=2',*a.disk]))
        print('After synchronization, explicitly select the new array for ext4 formatting, mount by filesystem UUID, and configure persistent mdadm assembly and the boot guard. Never format member disks.')
        return
    if not a.instance or not a.backup:p.error('Provide instance and verified independent backup')
    i=a.instance.resolve();b=a.backup.resolve()
    env=dict(x.split('=',1) for x in (i/'.env').read_text().splitlines() if '=' in x)
    if env.get('INSTANCE_DIR')!=str(i):p.error('Invalid instance')
    if i.stat().st_dev==b.stat().st_dev or i in b.parents or b in i.parents:p.error('Independent backup required')
    archive=verified_archives(b);old,_,_=metadata(archive['instance.tar.gz'])
    if old.get('COMPOSE_PROJECT_NAME')!=env.get('COMPOSE_PROJECT_NAME'):p.error('Backup belongs to another instance')
    source=source_for(i);node=nodes[source];md=read_md(source)
    # Refuse OS/Docker/backup devices and all their ancestors.
    docker=Path(subprocess.check_output(['docker','info','--format','{{.DockerRootDir}}'],text=True).strip())
    protected|=ancestry(nodes,source_for(docker))|ancestry(nodes,source_for(b))|ancestry(nodes,source)
    if a.action=='replace-member':
        if len(a.disk)!=1:p.error('Provide one approved unused whole disk')
        d=blank_disk(nodes,a.disk[0],protected);replacement(md,d)
        print('Verified backup belongs to instance. Review its freshness and actual restore before proceeding.')
        print('Approved plan (not executed):',shlex.join(['sudo','mdadm','--manage',source,'--add',a.disk[0]]))
        print('Monitor /proc/mdstat and SMART until fully synchronized. Do not remove the surviving drive.')
    else:
        if a.disk:p.error('Expansion uses existing synchronized members only')
        limit=expansion(md,nodes,node['fstype']);print('Upper capacity bound:',limit,'bytes; actual ext4 capacity will be lower.')
        print('Approved plan (not executed): stop this instance and all other users of the filesystem, verify restore, follow mdadm growth procedure, then expand ext4.')
        print(shlex.join(['sudo','mdadm','--grow',source,'--size=max']))
        print(shlex.join(['sudo','resize2fs',source]))
        print('Wait for synchronization and verify UUID, filesystem capacity, boot guard and app data before restarting. Do not execute both steps blindly.')
    print('No disk or filesystem changes were made.')
if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as e:sys.exit('Storage plan refused: '+str(e))
