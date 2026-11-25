import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('scan_release',Path(__file__).with_name('scan-release.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_severity_and_license(self):
        v={'VulnerabilityID':'CVE-fixture','PkgName':'fixture','InstalledVersion':'1','FixedVersion':'','Severity':'HIGH'}
        r=m.summarize({'Results':[{'Vulnerabilities':[v,v,{**v,'Severity':'LOW'},{**v,'Severity':'UNKNOWN'}],'Licenses':[{'Name':'MIT'},{'Name':'MIT'}]}]})
        self.assertEqual(len(r['vulnerabilities']),2);self.assertEqual(r['license_names'],['MIT'])
        self.assertTrue(any(x['fixed']=='' for x in r['vulnerabilities']))
        with self.assertRaises(ValueError):m.summarize({'Results':[]})
if __name__=='__main__':unittest.main()
