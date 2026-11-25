import importlib.util,unittest
from pathlib import Path
def load(name):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(name+'.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
class QualificationTests(unittest.TestCase):
    def test_reboot_evidence(self):
        q=load('qualify-appliance')
        base={'boot':'before','release':'release','data_mount':'data','backup_mount':'backup','health':{'alerts':[]}}
        self.assertFalse(q.compare(base,base)['different_boot'])
        result=q.compare(base,{**base,'boot':'after','data_mount':'wrong','health':{'alerts':['mount missing']}})
        self.assertTrue(result['different_boot']);self.assertFalse(result['same_data_mount']);self.assertEqual(result['post_boot_alerts'],['mount missing'])
if __name__=='__main__':unittest.main()
