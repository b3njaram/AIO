"""Disposable browser fixture: verify the exact UI/HTTP boundary, not real app provisioning."""
import importlib.util,tempfile,threading,time
from pathlib import Path
from unittest.mock import Mock
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
