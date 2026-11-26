import importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('monitors',Path(__file__).with_name('configure-monitors.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_existing_urls(self):
        self.assertEqual(m.missing({'dashboard':'http://dashboard:8080/healthz','music':'http://jobbi-music:3131/api/status'},{'1':{'type':'http','url':'http://dashboard:8080/healthz','name':'Customer chosen name'}}),{'music':'http://jobbi-music:3131/api/status'})
if __name__=='__main__':unittest.main()
