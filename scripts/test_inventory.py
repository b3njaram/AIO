import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('inventory',Path(__file__).with_name('release-inventory.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class InventoryTests(unittest.TestCase):
    def test_compare(self):
        a={'services':{'db':{'id':'one'},'web':{'id':'two'}}}
        self.assertEqual(m.compare(a,a),[])
        self.assertEqual(m.compare(a,{'services':{'db':{'id':'other'}}}),[{'service':'db','expected':'one','current':'other'},{'service':'web','expected':'two','current':None}])
if __name__=='__main__':unittest.main()
