import importlib.util,unittest,copy
from pathlib import Path
spec=importlib.util.spec_from_file_location('audit',Path(__file__).with_name('security-audit.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_runtime_rules(self):
        i=Path('/tmp/jobbi-audit-fixture');env={'COMPOSE_PROJECT_NAME':'jobbi-fixture','COMPOSE_PROFILES':'','BIND_IP':'127.0.0.1','TASK_REGISTRATION':'false','DASH_PORT':'18080','MUSIC_HTTPS':'false','MOVIE_HTTPS':'false','VAULT_DOMAIN':'http://127.0.0.1:18087','TASK_URL':'http://127.0.0.1:18088/'}
        c={'Id':'fixture','Config':{'Labels':{'com.docker.compose.project':'jobbi-fixture','com.docker.compose.service':'dashboard'},'Env':['SYNTHETIC_SECRET=not_for_output']},'HostConfig':{'RestartPolicy':{'Name':'unless-stopped'},'ReadonlyRootfs':True,'CapDrop':['ALL'],'SecurityOpt':['no-new-privileges:true'],'PortBindings':{'8080/tcp':[{'HostIp':'127.0.0.1','HostPort':'18080'}]}},'State':{'Running':True},'NetworkSettings':{'Ports':{'8080/tcp':[{'HostIp':'127.0.0.1','HostPort':'18080'}]},'Networks':{'jobbi-fixture_default':{}}},'Mounts':[]}
        n={'Name':'jobbi-fixture_default','Labels':{'com.docker.compose.project':'jobbi-fixture'},'Containers':{'fixture':{}}}
        self.assertEqual(m.findings(i,env,[c],[n]),[])
        for k,v in [('Privileged',True),('NetworkMode','host'),('ReadonlyRootfs',False),('PortBindings',{'8080/tcp':[{'HostIp':'0.0.0.0','HostPort':'18080'}]})]:
            changed=copy.deepcopy(c);changed['HostConfig'][k]=v;self.assertTrue(m.findings(i,env,[changed],[n]))
        changed=copy.deepcopy(c);changed['Mounts']=[{'Source':'/var/run/docker.sock','Destination':'/var/run/docker.sock','Type':'bind','RW':True}]
        self.assertIn('engine_socket_mount',[x['check'] for x in m.findings(i,env,[changed],[n])])
        self.assertTrue(m.findings(i,env,[c],[{**n,'Containers':{'fixture':{},'foreign':{}}}]))
if __name__=='__main__':unittest.main()
