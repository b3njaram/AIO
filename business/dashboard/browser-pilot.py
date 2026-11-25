"""Run from CI with Playwright. All records and reports are synthetic and temporary."""
import json,os,secrets,subprocess,sys,tempfile,time,urllib.request,urllib.error,base64
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
        proc=subprocess.Popen([sys.executable,str(ROOT/'business/dashboard/server.py'),'--port','18790','--allow-origin','http://macmini2012:18790','--allow-origin','https://macmini2012.demo.ts.net'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        base='http://127.0.0.1:18790'
        try:
            auth='Basic '+base64.b64encode(('owner:'+password).encode()).decode()
            for _ in range(40):
                if proc.poll() is not None:raise RuntimeError('Dashboard failed to start')
                try:
                    with urllib.request.urlopen(urllib.request.Request(base+'/api/init',headers={'Authorization':auth}),timeout=2):break
                except OSError:time.sleep(.25)
            else:raise RuntimeError('Dashboard not reachable')
            def status(host,origin=None,authorized=True):
                headers={'Host':host}
                if authorized:headers['Authorization']=auth
                method='GET' if origin is None else 'POST'
                if origin is not None:headers.update({'Origin':origin,'Content-Type':'application/json','X-Jobbi-Request':'1'})
                req=urllib.request.Request(base+('/api/init' if origin is None else '/api/nonexistent'),headers=headers,method=method,data=None if origin is None else b'{}')
                try:
                    with urllib.request.urlopen(req,timeout=5) as response:return response.status
                except urllib.error.HTTPError as error:return error.code
            assert status('macmini2012:18790')==200
            assert status('macmini2012.demo.ts.net')==200
            assert status('macmini2012:18790',authorized=False)==401
            assert status('unapproved.example')==403
            assert status('macmini2012:18790','http://macmini2012:18790')==404
            assert status('macmini2012.demo.ts.net','https://macmini2012.demo.ts.net')==404
            assert status('macmini2012:18790','http://127.0.0.1:18790')==403
            assert status('127.0.0.1:18790','http://macmini2012:18790')==403
            assert status('macmini2012:18790','https://evil.example')==403
            assert status('macmini2012.demo.ts.net','http://macmini2012.demo.ts.net')==403
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page(http_credentials={'username':'owner','password':password},accept_downloads=True)
                errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(base)
                expect(page.locator('#overview')).to_be_visible()
                expect(page.locator('.quick-actions')).to_have_count(0)
                page.locator('nav [data-tab=hardware]').click()
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
                page.locator('#paymentPanel > summary').click()
                p=page.locator('#payment');fill(p,'transaction','TX1');fill(p,'amount','100');p.get_by_role('button',name='Record cash').click()
                expect(page.get_by_text('Cash recorded. Issue applicable receipt separately.')).to_be_visible()
                page.locator('nav [data-tab=installation]').click()
                page.locator('#planPanel > summary').click()
                q=page.locator('#planForm');select(q,'order_id','DEMO-1');fill(q,'name','demo1')
                q.get_by_role('button',name='Generate installation plan').click()
                expect(page.locator('#planOutput')).to_contain_text('--name demo1')
                page.locator('#eventPanel > summary').click()
                event=page.locator('#eventForm')
                select(event,'step','storage');select(event,'result','passed');fill(event,'note','Verified synthetic mount')
                event.get_by_role('button').click()
                expect(page.locator('#eventList')).to_contain_text('Verified synthetic mount')
                page.locator('nav [data-tab=support]').click()
                page.locator('#componentPanel > summary').click()
                component=page.locator('#componentForm')
                fill(component,'component','Drive A');fill(component,'provider','Demo vendor');fill(component,'expires','2028-12-31')
                component.get_by_role('button').click()
                expect(page.locator('#componentList')).to_contain_text('Drive A')
                page.locator('#casePanel > summary').click()
                case=page.locator('#caseForm');fill(case,'id','CASE1');fill(case,'subject','Synthetic support');case.get_by_role('button',name='Save case').click()
                expect(page.get_by_role('heading',name='CASE1 · Synthetic support')).to_be_visible()
                page.locator('nav [data-tab=documents]').click()
                page.get_by_text('Plain text draft',exact=True).click()
                h=page.locator('#handoffForm');select(h,'lang','es')
                with page.expect_download() as d:h.get_by_role('button',name='Download handoff draft').click()
                assert 'Folio: DEMO-1' in Path(d.value.path()).read_text()
                documents=page.locator('#documentForm')
                select(documents,'lang','es')
                for kind in ('quote','handoff','receipt','acceptance'):
                    select(documents,'kind',kind)
                    if kind=='receipt':select(documents,'transaction','TX1')
                    with page.expect_download() as d:
                        documents.get_by_role('button').click()
                    assert Path(d.value.path()).read_bytes().startswith(b'%PDF-')
                page.reload()
                page.locator('nav [data-tab=orders]').click()
                expect(page.get_by_role('heading',name='DEMO-1 · Synthetic order')).to_be_visible()
                page.locator('#dashboardLanguage').select_option('es')
                expect(page.locator('nav [data-tab=orders]')).to_have_text('Pedidos y garantías')
                page.locator('#orderPanel > summary').click()
                expect(page.locator('#order').get_by_role('button',name='Guardar pedido')).to_be_visible()
                page.reload()
                expect(page.locator('html')).to_have_attribute('lang','es')
                page.set_viewport_size({'width':390,'height':844})
                page.locator('nav [data-tab=overview]').click()
                expect(page.locator('#overview')).to_be_visible()
                expect(page.locator('#recentPayments')).to_contain_text('DEMO-1')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth + 1')
                assert not errors,errors
                browser.close()
            print('PASS: browser hardware confirmation, BOM, pricing, cash order, install plan, support case, handoff and persistence')
        finally:
            proc.terminate();proc.wait(timeout=10)
def no_login_demo():
    with tempfile.TemporaryDirectory() as tmp:
        env={**os.environ,'HOME':tmp}
        command=[sys.executable,str(ROOT/'business/dashboard/server.py'),'--preview-no-auth','--port','8791','--allow-origin','http://macmini2012:8791']
        proc=subprocess.Popen(command,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        base='http://127.0.0.1:8791'
        def request(path,host='macmini2012:8791',origin=None):
            headers={'Host':host}
            if origin:headers.update({'Origin':origin,'X-Jobbi-Request':'1','Content-Type':'application/json'})
            req=urllib.request.Request(base+path,headers=headers,data=b'{}' if origin else None)
            try:
                with urllib.request.urlopen(req,timeout=3) as response:return response.status,response.read()
            except urllib.error.HTTPError as error:return error.code,error.read()
        try:
            for _ in range(40):
                if proc.poll() is not None:raise RuntimeError('Demo failed to start')
                try:
                    code,body=request('/api/init')
                    if code==200:break
                except OSError:time.sleep(.25)
            else:raise RuntimeError('Demo unavailable')
            assert json.loads(body)['preview'] is True
            assert request('/api/init',host='unapproved.example')[0]==403
            assert request('/api/search',origin='http://macmini2012:8791')[0]==403
            assert request('/api/nonexistent',origin='http://evil.example')[0]==403
            assert request('/api/nonexistent',origin='http://macmini2012:8791')[0]==404
            assert (Path(tmp)/'.jobbi-no-login-demo/cash.sqlite3').exists()
            assert not (Path(tmp)/'.local/share/jobbi-business/cash.sqlite3').exists()
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page()
                page.goto(base)
                expect(page.locator('#demoNotice')).to_be_visible()
                expect(page.locator('#overview')).to_be_visible()
                browser.close()
        finally:proc.terminate();proc.wait(timeout=10)
        denied=subprocess.run(command+['--port','8790'],env=env,capture_output=True,timeout=10)
        assert denied.returncode!=0
    print('PASS: no-login preview, separate data, offline sourcing, host/origin rejection and production-port refusal')
if __name__=='__main__':main();no_login_demo()
