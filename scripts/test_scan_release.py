import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('scan_release',Path(__file__).with_name('scan-release.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_severity_and_license(self):
        v={'VulnerabilityID':'CVE-fixture','PkgName':'fixture','InstalledVersion':'1','FixedVersion':'','Severity':'HIGH'}
        r=m.summarize({'Results':[{'Vulnerabilities':[v,v,{**v,'Severity':'LOW'},{**v,'Severity':'MEDIUM'},{**v,'Severity':'UNKNOWN'}],'Licenses':[{'Name':'MIT'},{'Name':'MIT'}]}]})
        self.assertEqual({x['severity'] for x in r['vulnerabilities']}, {'HIGH', 'LOW', 'MEDIUM', 'UNKNOWN'})
        self.assertEqual(len(r['vulnerabilities']), 4)
        self.assertEqual(r['license_names'], ['MIT'])
        self.assertTrue(any(x['fixed']=='' for x in r['vulnerabilities']))
        with self.assertRaises(ValueError):m.summarize({'Results':[]})
    def test_distinct_install_paths_remain_visible_without_changing_gate(self):
        v={'VulnerabilityID':'CVE-fixture','PkgName':'example','InstalledVersion':'1','FixedVersion':'2','Severity':'HIGH'}
        result=m.summarize({'Results':[{'Target':'runtime','Type':'python','Vulnerabilities':[{**v,'PkgPath':'/venv/pkg'},{**v,'PkgPath':'/global/pkg'}]}]})
        self.assertEqual(len(result['vulnerabilities']),1)
        self.assertEqual({x['package_path'] for x in result['advisories']},{'/venv/pkg','/global/pkg'})
if __name__=='__main__':unittest.main()
