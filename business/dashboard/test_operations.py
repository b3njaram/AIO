import unittest
import operations as o
class Tests(unittest.TestCase):
    def test_plan(self):
        d=dict(name='customer1',root='/srv/data',backup='/mnt/backup',apps=['music','monitor'],port='18080',tb='4',ram='16',tz='Etc/UTC',mirror=True)
        p=o.plan(d);self.assertIn('--apps music,monitor',p['commands']);self.assertIn('/srv/data/customer1',p['commands'])
        with self.assertRaises(ValueError):o.plan({**d,'name':'x;echo hi'})
        with self.assertRaises(ValueError):o.plan({**d,'apps':['dns']})
        with self.assertRaises(ValueError):o.plan({**d,'backup':'/srv/data/backups'})
    def test_handoff(self):
        x=dict(id='TEST',market='MX',total=10000,paid=1000,delivered=None,support_end=None,warranty_end=None,installation_warranty_end=None)
        self.assertIn('Folio: TEST',o.handoff(x,None,'es'))
        self.assertIn('Order: TEST',o.handoff(x,None,'en'))
if __name__=='__main__':unittest.main()
