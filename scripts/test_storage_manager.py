import unittest
from storage_manager import ancestry,replacement,expansion
class StorageTests(unittest.TestCase):
    def test_ancestry(self):
        nodes={'/dev/md0':{'parents':{'/dev/sda','/dev/sdb'}},'/dev/sda':{'parents':set()},'/dev/sdb':{'parents':set()}}
        self.assertEqual(ancestry(nodes,'/dev/md0'),set(nodes))
    def test_replace(self):
        md={'level':'raid1','expected':2,'degraded':1,'sync_action':'idle','array_state':'clean','component_bytes':100,'members':[{'device':'/dev/sda','state':['in_sync']}]}
        replacement(md,{'size':100})
        for change in ({'degraded':0},{'degraded':2},{'sync_action':'recover'},{'members':[]},{'level':'raid0'}):
            with self.assertRaises(ValueError):replacement({**md,**change},{'size':100})
        with self.assertRaises(ValueError):replacement(md,{'size':99})
    def test_expand(self):
        md={'level':'raid1','expected':2,'degraded':0,'sync_action':'idle','component_bytes':1024,'members':[{'device':x,'state':['in_sync']} for x in ('a','b')]}
        self.assertEqual(expansion(md,{'a':{'size':10**9},'b':{'size':2*10**9}},'ext4'),10**9)
        with self.assertRaises(ValueError):expansion(md,{'a':{'size':1024},'b':{'size':2*10**9}},'ext4')
        with self.assertRaises(ValueError):expansion(md,{},'xfs')
if __name__=='__main__':unittest.main()
