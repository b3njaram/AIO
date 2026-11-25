import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_private_access import m as access
import private_routes

class RouteTests(unittest.TestCase):
    def test_apply_interruption_and_rollback(self):
        host='customer.example.ts.net'
        plan={'dashboard':{'target':'http://127.0.0.1:18080','port':19443},
              'music':{'target':'http://127.0.0.1:18081','port':19444}}
        state={'TCP':{},'Web':{}}
        def run(cmd,**kwargs):
            port=next(s.split('=')[1] for s in cmd if s.startswith('--https='))
            if cmd[-1]=='off':
                del state['TCP'][port],state['Web'][host+':'+port]
            elif port=='19444':
                raise OSError('interruption')
            else:
                state['TCP'][port]={'HTTPS':True}
                state['Web'][host+':'+port]={'Handlers':{'/':{'Proxy':cmd[-1]}}}
        with tempfile.TemporaryDirectory() as tmp,patch.object(private_routes,'serve_status',return_value=state),patch.object(private_routes,'verify_backends'),patch.object(private_routes.subprocess,'run',side_effect=run):
            i=Path(tmp)
            args=(access.verify_config,access.existing_conflicts)
            with self.assertRaises(OSError):
                private_routes.manage(i,plan,host,False,*args)
            self.assertEqual(set(state['TCP']),{'19443'})
            state['TCP']['443']={'HTTPS':True}
            with self.assertRaises(ValueError):
                private_routes.manage(i,plan,host,True,*args)
            del state['TCP']['443']
            private_routes.manage(i,{},host,True,*args)
            self.assertFalse(state['TCP'])
            self.assertFalse((i/'.private-serve.json').exists())
