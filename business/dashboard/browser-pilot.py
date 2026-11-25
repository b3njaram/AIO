"""Run from CI with Playwright. All records and reports are synthetic and temporary."""
import json,os,secrets,subprocess,sys,tempfile,time,urllib.request,base64
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
ROOT=Path(__file__).resolve().parents[2]
def main():
    assert os.environ.get('GITHUB_ACTIONS')=='true','CI only'
    with tempfile.TemporaryDirectory() as tmp:
        home=Path(tmp);env={**os.environ,'HOME':tmp}
        config=home/'.config/jobbi-business';config.mkdir(parents=True)
        password=secrets.token_urlsafe(32)
        p=config/'dashboard-password';p.write_text(password+'\n');p.chmod(0o600)
        reports=home/'.local/share/jobbi-business/sourcing/family-20260101T000000000000Z'
        reports.mkdir(parents=True)
        offers={'offers':[{'market':'US','part':'computer','supplier':'eBay','title':'Dell OptiPlex 7060 MT i5 16GB 256GB SSD','price':'150','shipping':'20','condition':'Used','currency':'USD','decision':'candidate','reason':'Check hardware','url':'https://www.ebay.com/itm/123456789','notes':'Synthetic fixture'}],'coverage':[['Fixture','No live data']],'bom':[]}
        (reports/'offers.json').write_text(json.dumps(offers))
        proc=subprocess.Popen([sys.executable,str(ROOT/'business/dashboard/server.py'),'--port','18790'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        base='http://127.0.0.1:18790'
        try:
            auth='Basic '+base64.b64encode(('owner:'+password).encode()).decode()
            for _ in range(40):
                if proc.poll() is not None:raise RuntimeError('Dashboard failed to start')
                try:
                    with urllib.request.urlopen(urllib.request.Request(base+'/api/init',headers={'Authorization':auth}),timeout=2):break
                except OSError:time.sleep(.25)
            else:raise RuntimeError('Dashboard not reachable')
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page(http_credentials={'username':'owner','password':password},accept_downloads=True)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base)
                expect(page.get_by_text('Dell OptiPlex 7060 MT i5 16GB 256GB SSD')).to_be_visible()
                page.locator('#target').select_option('US')
                form=page.locator('#confirm')
                def fill(form,name,value):form.locator('[name="'+name+'"]').fill(str(value))
                def select(form,name,value):form.locator('[name="'+name+'"]').select_option(value)
                page.get_by_role('button',name='Review / confirm').click()
                fill(form,'exact_model','Dell OptiPlex 7060 MT i5 16GB 256GB SSD');select(form,'condition','used')
                for k,v in {'available_quantity':'1','unit_price':'150','unit_shipping':'20','unit_tax':'10','unit_import':'0','warranty':'Verified US warranty'}.items():fill(form,k,v)
                form.locator('[name=compatibility_checked]').check();form.locator('[name=confirmed]').check()
                form.get_by_role('button',name='Save confirmed offer').click()
                expect(page.get_by_text('Confirmed offer saved.')).to_be_visible()
                select(form,'part','hdd');select(form,'supplier','eBay');fill(form,'url','https://www.ebay.com/itm/987654321');fill(form,'exact_model','WD40EFPX');select(form,'condition','new')
                for k,v in {'available_quantity':'2','unit_price':'100','unit_shipping':'0','unit_tax':'5','unit_import':'0','warranty':'Verified US warranty'}.items():fill(form,k,v)
                form.locator('[name=compatibility_checked]').check();form.locator('[name=confirmed]').check()
                form.get_by_role('button',name='Save confirmed offer').click()
                expect(page.get_by_text('Lowest complete confirmed build: $390.00')).to_be_visible()
                page.get_by_role('button',name='Use confirmed hardware cost in profitability').click()
                c=page.locator('#cost')
                expect(c.locator('[name=hardware]')).to_have_value('390.00')
                for k,v in {'labor':'50','support':'20','shipping':'0','warranty':'20','overhead':'10'}.items():fill(c,k,v)
                c.get_by_role('button',name='Calculate').click()
                expect(page.get_by_text('Calculation complete; verify tax and final agreed amount.')).to_be_visible()
                page.get_by_role('button',name='Start order from calculated price').click()
                o=page.locator('#order');fill(o,'id','DEMO-1');fill(o,'label','Synthetic order');o.get_by_role('button',name='Save order').click()
                expect(page.get_by_role('heading',name='DEMO-1 · Synthetic order')).to_be_visible()
                p=page.locator('#payment');fill(p,'transaction','TX1');fill(p,'amount','100');p.get_by_role('button',name='Record cash').click()
                expect(page.get_by_text('Cash recorded. Issue applicable receipt separately.')).to_be_visible()
                page.get_by_role('button',name='Installation',exact=True).click()
                q=page.locator('#planForm');select(q,'order_id','DEMO-1');fill(q,'name','demo1')
                q.get_by_role('button',name='Generate installation plan').click()
                expect(page.locator('#planOutput')).to_contain_text('--name demo1')
                page.get_by_role('button',name='Support & handoff').click()
                case=page.locator('#caseForm');fill(case,'id','CASE1');fill(case,'subject','Synthetic support');case.get_by_role('button',name='Save case').click()
                expect(page.get_by_role('heading',name='CASE1 · Synthetic support')).to_be_visible()
                h=page.locator('#handoffForm');select(h,'lang','es')
                with page.expect_download() as d:h.get_by_role('button',name='Download handoff draft').click()
                assert 'Folio: DEMO-1' in Path(d.value.path()).read_text()
                page.reload()
                page.get_by_role('button',name='Orders & warranty').click()
                expect(page.get_by_role('heading',name='DEMO-1 · Synthetic order')).to_be_visible()
                assert not errors,errors
                browser.close()
            print('PASS: browser hardware confirmation, BOM, pricing, cash order, install plan, support case, handoff and persistence')
        finally:
            proc.terminate();proc.wait(timeout=10)
if __name__=='__main__':main()
