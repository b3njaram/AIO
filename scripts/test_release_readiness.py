import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('readiness',Path(__file__).with_name('release-readiness.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_exact_and_skipped(self):
        sha='a'*40
        def fake(path):
            if '/workflows/' in path:
                name=path.split('/workflows/')[1].split('/')[0]
                id=list(m.GATES).index(name)+1
                return {'workflow_runs':[{'id':id,'head_sha':sha,'event':'push','status':'completed','conclusion':'success'}]}
            id=int(path.split('/runs/')[1].split('/')[0]);name=list(m.GATES)[id-1]
            return {'jobs':[{'name':j,'status':'completed','conclusion':'success'} for j in m.GATES[name]]}
        r=m.evaluate(sha,fake);self.assertTrue(r['software_gates_passed']);self.assertFalse(r['commercial_release_approved'])
        def skipped(path):
            if '/runs/2/jobs' in path:
                data=fake(path);data['jobs'][1]['conclusion']='skipped';return data
            return fake(path)
        self.assertFalse(m.evaluate(sha,skipped)['software_gates_passed'])
        def wrong(path):
            r=fake(path)
            if 'workflow_runs' in r:r['workflow_runs'][0]['head_sha']='b'*40
            return r
        self.assertFalse(m.evaluate(sha,wrong)['software_gates_passed'])
        def newer_failure(path):
            r=fake(path)
            if '/workflows/pilot.yml/' in path:
                r['workflow_runs'].append({'id':999,'head_sha':sha,'event':'workflow_dispatch','status':'completed','conclusion':'failure'})
            if '/runs/999/jobs' in path:return {'jobs':[{'name':'isolation','status':'completed','conclusion':'failure'}]}
            return r
        # A recent failed execution is never masked by an older successful run.
        def failure(path):
            if '/runs/999/jobs' in path:return {'jobs':[{'name':'isolation','status':'completed','conclusion':'failure'}]}
            return newer_failure(path)
        self.assertFalse(m.evaluate(sha,failure)['software_gates_passed'])
if __name__=='__main__':unittest.main()
