"""CI-only test of the guided quote and preserved calculator/download workflow."""
import json,subprocess,sys,time,urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parent
def main():
    server=subprocess.Popen([sys.executable,'-m','http.server','18792','--bind','127.0.0.1','--directory',str(ROOT)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        for _ in range(40):
            try:urllib.request.urlopen('http://127.0.0.1:18792/',timeout=1).close();break
            except OSError:time.sleep(.25)
        else:raise RuntimeError('Quote preview unavailable')
        with sync_playwright() as pw:
            browser=pw.chromium.launch()
            for width in (1280,390):
                page=browser.new_page(viewport={'width':width,'height':850},locale='en-US',accept_downloads=True,reduced_motion='reduce')
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto('http://127.0.0.1:18792/')
                expect(page.locator('#capacity')).to_have_text('8 TB')
                expect(page.locator('[data-page="1"]')).to_be_hidden()
                initial=page.locator('#livePrice').inner_text()
                page.locator('#tb').fill('12')
                expect(page.locator('#livePrice')).not_to_have_text(initial)
                page.locator('#next').click()
                expect(page.locator('#apps')).to_be_visible()
                page.locator('[data-app="dns"]').check()
                page.locator('#next').click()
                expect(page.locator('#subs')).to_be_visible()
                page.locator('#subs input[type=checkbox]').first.check()
                page.locator('#support').select_option('12')
                page.locator('#next').click()
                expect(page.locator('#reviewPrice')).to_have_text(page.locator('#livePrice').inner_text())
                expect(page.locator('#stats')).to_be_visible()
                with page.expect_download() as d:page.locator('#export').click()
                data=json.loads(Path(d.value.path()).read_text())
                assert data['requestedTB']==12 and data['supportMonths']==12 and 'dns' in data['apps']
                assert page.locator('#request').get_attribute('href').startswith('mailto:')
                page.locator('#es').click()
                expect(page.locator('html')).to_have_attribute('lang','es')
                expect(page.locator('#reviewPrice')).to_be_visible()
                page.locator('[data-step="0"]').click()
                expect(page.locator('#capacity')).to_have_text('12 TB')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                assert not errors,errors
                page.close()
            browser.close()
        print('PASS: responsive guided quote, live pricing, app choices, support, JSON export, Spanish and state preservation')
    finally:server.terminate();server.wait(timeout=5)
if __name__=='__main__':main()
