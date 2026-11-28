import copy,json,unittest
from unittest.mock import Mock
import prowlarr_setup as m

class Tests(unittest.TestCase):
    def setUp(self):
        self.row={'name':'Fixture','implementation':'Cardigann','definitionName':'fixture','protocol':'torrent','fields':[{'name':'apiKey','label':'API key','type':'password','value':'do-not-return'},{'name':'mode','type':'select','selectOptions':[{'value':1,'name':'One'}]},{'name':'internal','type':'hidden','value':'hidden'}]}
        self.id=m.identity(self.row)
        self.installed=[]
        self.ops=[]
    def call(self,path,data=None):
        self.ops.append((path,copy.deepcopy(data)))
        if path.endswith('/schema'):return [copy.deepcopy(self.row)]
        if path.endswith('/test'):return None
        if data is None:return self.installed
        self.installed.append({'name':data['name'],'enable':True})
        return {'id':2}
    def test_catalog_and_fields_redacted(self):
        for action in ({'action':'list'},{'action':'fields','id':self.id}):
            result=m.handle(self.call,action)
            self.assertNotIn('do-not-return',json.dumps(result))
            self.assertNotIn('hidden',json.dumps(result))
    def test_test_before_create_and_duplicate_refused(self):
        data={'action':'add','id':self.id,'name':'Customer fixture','values':{'apiKey':'customer-secret','mode':1},'consent':True}
        self.assertTrue(m.handle(self.call,data)['created'])
        self.assertEqual([op[0] for op in self.ops][-2:],['/api/v1/indexer/test','/api/v1/indexer'])
        self.assertEqual(self.ops[-1][1]['fields'][0]['value'],'customer-secret')
        with self.assertRaises(ValueError):m.handle(self.call,data)
        with self.assertRaises(ValueError):m.handle(self.call,{**data,'name':'Other','values':{'internal':'overwrite'}})
        with self.assertRaises(ValueError):m.handle(self.call,{**data,'name':'Other','consent':False})
    def test_failed_test_never_creates(self):
        def fail(path,data=None):
            if path.endswith('/test'):raise ValueError('fixture')
            return self.call(path,data)
        with self.assertRaises(ValueError):m.handle(fail,{'action':'add','id':self.id,'name':'Customer fixture','values':{},'consent':True})
        self.assertFalse(self.installed)
