import datetime as dt,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('launch',Path(__file__).with_name('launch-review.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_deferred_never_passes(self):
        sha='a'*40;d=m.template(sha);ci={'commit':sha,'software_gates_passed':True}
        d['gates']['hardware']['state']='deferred'
        self.assertFalse(m.review(sha,d,ci)['all_documented'])
        for x in d['gates'].values():x.update(state='reviewed',reference='fixture',reviewed_at=dt.datetime.now(dt.timezone.utc).isoformat())
        self.assertTrue(m.review(sha,d,ci)['all_documented'])
        self.assertFalse(m.review(sha,d,ci)['commercial_release_approved'])
        self.assertFalse(m.review(sha,d,{'commit':'b'*40,'software_gates_passed':True})['all_documented'])
        d['gates']['licensing']['reference']=''
        with self.assertRaises(ValueError):m.review(sha,d,ci)
if __name__=='__main__':unittest.main()
