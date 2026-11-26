import importlib.util,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,Mock
spec=importlib.util.spec_from_file_location('boot_recover',Path(__file__).with_name('boot-recover.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
    def test_start_existing_launcher_and_preserve_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=Path(tmp)/'home';i.mkdir()
            (i/'.env').write_text('INSTANCE_DIR='+str(i)+'\nCOMPOSE_PROJECT_NAME=jobbi-home\nOWNER_UID=1000\nDASH_PORT=18080\n')
            run=Mock()
            with patch.object(m,'mount_identity',return_value='approved'),patch.object(m.os,'geteuid',return_value=1000),patch.object(m.os,'getuid',return_value=1000):
                m.recover(i,'approved',run=run,ready=Mock(side_effect=[False,True]))
                self.assertEqual(run.call_args.args[0][-2:],['start','dashboard'])
                run.reset_mock()
                (i/'.upgrade-hold.json').touch()
                m.recover(i,'approved',run=run,ready=lambda:False)
                run.assert_not_called()
                (i/'.upgrade-hold.json').unlink()
                (i/'.backup-running-services').touch()
                with self.assertRaisesRegex(ValueError,'Interrupted backup'):m.recover(i,'approved',run=run)
                with self.assertRaisesRegex(ValueError,'filesystem'):m.recover(i,'wrong',run=run)
                run.assert_not_called()
if __name__=='__main__':unittest.main()
