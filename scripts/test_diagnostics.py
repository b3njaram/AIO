import unittest
from diagnostics import parse_smart
class SmartTests(unittest.TestCase):
    def test_pass(self):
        self.assertEqual(parse_smart({'smart_status':{'passed':True}},0)['state'],'passed')
    def test_failure(self):
        self.assertEqual(parse_smart({'smart_status':{'passed':False}},8)['state'],'failed')
        self.assertEqual(parse_smart({'nvme_smart_health_information_log':{'critical_warning':1}},0)['state'],'failed')
    def test_unknown(self):
        self.assertEqual(parse_smart({'smart_status':{'passed':True}},2)['state'],'unknown')
        self.assertEqual(parse_smart({},0)['state'],'unknown')
    def test_history(self):
        self.assertEqual(parse_smart({'smart_status':{'passed':True},'ata_smart_attributes':{'table':[{'id':197,'raw':{'value':2}}]}},0)['state'],'review')
if __name__=='__main__':unittest.main()
