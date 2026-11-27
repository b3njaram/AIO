"""Disposable browser fixture: verify the exact UI/HTTP boundary, not real app provisioning."""
import importlib.util,tempfile,threading,time
from pathlib import Path
from unittest.mock import Mock,patch
from playwright.sync_api import sync_playwright,expect
spec=importlib.util.spec_from_file_location('setup_web',Path(__file__).with_name('setup-web.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as tmp:
    adapter=Mock();adapter.env_for.return_value={'COMPOSE_PROFILES':'music,passwords','MUSIC_ADMIN':'owner'}
    adapter.create.side_effect=lambda *args:time.sleep(1.5)
    session=m.Session(Path(tmp),adapter=adapter);server=m.Server(0,session);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(server.origin);page.locator('#code').fill(session.token);page.locator('#unlockButton').click()
            expect(page.locator('#appTitle')).to_have_text('All supported accounts')
            page.locator('#email').fill('owner@example.invalid');page.locator('#password').fill('fixture-password');page.locator('#confirm').fill('fixture-password')
            page.locator('#createButton').click();expect(page.locator('#progressText')).to_contain_text('Configuring Jobbi Music');expect(page.locator('#password')).to_have_value('');expect(page.locator('#appTitle')).to_have_text('Vaultwarden')
            expect(page.locator('#passwordFields')).to_be_hidden();expect(page.locator('#password')).to_have_value('')
            page.locator('#createButton').click();expect(page.locator('#progressText')).to_contain_text('2 / 2')
            page.locator('#lang').click();expect(page.locator('#title')).to_have_text('Configura tu hogar')
            expect(page.locator('#finish')).to_be_enabled();page.locator('#finish').click();expect(page.locator('#wizard')).to_be_hidden()
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')
            adapter.create.assert_called_once();adapter.invite_vault.assert_called_once()
            browser.close()
    finally:server.shutdown();server.server_close();thread.join()
print('PASS: local setup wizard, password clearing, invitation, Spanish, mobile and session closure (mock app adapter)')

# Paired options fixture: mock only external provisioning. Real browser,
# authentication, validation, password handling and recheck API remain in use.
with tempfile.TemporaryDirectory() as tmp:
    adapter=Mock();adapter.env_for.return_value={'COMPOSE_PROFILES':'music,passwords','MUSIC_ADMIN':'owner'}
    instance=Path(tmp);session=m.Session(instance,adapter=adapter);session.done=set(session.apps);session.lan={'address':'192.168.1.168'}
    option_state={}
    def provision(i,address,selected,pw):
        assert i==instance and address=='192.168.1.168'
        assert selected==['dns'] and pw=='fixture-dns-password'
        option_state.update(dns='review')
        return option_state
    def recheck(i):
        assert i==instance
        option_state.update(dns='ready')
        return option_state
    server=m.Server(0,session);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with patch.object(m.pilot_options,'read',side_effect=lambda i:dict(option_state)),patch.object(m.pilot_options,'provision',side_effect=provision) as provision_mock,patch.object(m.pilot_options,'reconcile',side_effect=recheck) as recheck_mock,patch.object(m.pilot_options,'tailnet_status',return_value={'state':'NeedsLogin'}),patch.object(m.pilot_options,'tailnet_connect',return_value={'state':'NeedsLogin'}) as connect_mock,sync_playwright() as pw:
            browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(server.origin);page.locator('#code').fill(session.token);page.locator('#unlockButton').click()
            expect(page.locator('#optional')).to_be_visible()
            page.locator('#optDns').check();page.locator('#dnsPassword').fill('fixture-dns-password')
            page.locator('#activateOptions').click();expect(page.locator('#status')).to_contain_text('authorize')
            provision_mock.assert_not_called()
            page.locator('#optConsent').check();page.locator('#activateOptions').click()
            expect(page.locator('#optionalStatus')).to_contain_text('needs review')
            expect(page.locator('#dnsPassword')).to_have_value('')
            expect(page.locator('#optDns')).to_be_disabled()
            page.locator('#recheckOptions').click();expect(page.locator('#optionalStatus')).to_contain_text('service probe passed')
            page.locator('#connectTailnet').click();expect(page.locator('#connectTailnet')).to_be_enabled()
            assert provision_mock.call_count==1 and recheck_mock.call_count==1 and connect_mock.call_count==1
            browser.close()
    finally:server.shutdown();server.server_close();thread.join()
print('PASS: paired optional-service browser consent, password clearing, retained state, recheck and tailnet enrollment (mock external services)')

# Actual browser/API approval boundary; external Tailscale commands are mocked.
with tempfile.TemporaryDirectory() as tmp:
    adapter=Mock();adapter.env_for.return_value={'COMPOSE_PROFILES':'music,passwords','MUSIC_ADMIN':'owner'}
    instance=Path(tmp);session=m.Session(instance,adapter=adapter);session.done=set(session.apps);session.lan={'address':'192.168.1.168'}
    host='customer.example.ts.net';url='https://'+host+':19443/'
    import pilot_tailnet
    server=m.Server(0,session);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with patch.object(m.pilot_options,'read',return_value={}),patch.object(m.pilot_options,'tailnet_status',return_value={'state':'Running','host':host}),patch.object(pilot_tailnet,'finish',return_value=url) as finish_mock,sync_playwright() as pw:
            browser=pw.chromium.launch();page=browser.new_page(viewport={'width':390,'height':844})
            page.goto(server.origin);page.locator('#code').fill(session.token);page.locator('#unlockButton').click()
            expect(page.locator('#tailnetFinish')).to_be_visible()
            expect(page.locator('#tailnetHost')).to_have_text(host)
            expect(page.locator('#finishTailnetButton')).to_be_disabled()
            finish_mock.assert_not_called()
            page.locator('#tailnetConsent').check();page.locator('#finishTailnetButton').click()
            expect(page.locator('#finishedUrl')).to_have_attribute('href',url)
            expect(page.locator('#wizard')).to_be_hidden()
            finish_mock.assert_called_once_with(instance,{'consent':True,'host':host},{'state':'Running','host':host},{})
            assert session.closed and not (instance/'.pilot-lan-client.json').exists()
            browser.close()
    finally:server.shutdown();server.server_close();thread.join()
print('PASS: paired Tailscale host-bound approval and private URL handoff (mock external routes)')
