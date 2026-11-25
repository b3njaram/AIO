#!/usr/bin/env python3
"""Private sourcing report. Searches approved APIs only; never purchases hardware."""
import argparse, csv, datetime as dt, html, json, os, re, sys, urllib.parse as u, subprocess
from dealcompare_bridge import load_env, connect, search as deal_search
from retailers import links, collect
from pathlib import Path
from decimal import Decimal, InvalidOperation
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
CAT=json.loads((ROOT/'catalog.json').read_text())
MARKETS={'US':('USD','en','El Paso, Texas, United States'),'MX':('MXN','es','Ciudad Juarez, Chihuahua, Mexico')}
def dec(x):
    try:
        d=Decimal(str(x))
        return d if d.is_finite() and 0<=d<=100000000 else None
    except (InvalidOperation,ValueError,TypeError): return None
def safe_url(x):
    try:
        p=u.urlsplit(str(x))
        if p.scheme=='https' and p.hostname and not p.username and not p.password and p.port in (None,443):
            return u.urlunsplit(('https',p.netloc,p.path,p.query,''))
    except ValueError: pass
    return ''
def domain_is(url,domain):
    try:
        host=u.urlsplit(url).hostname or ''
        return host==domain or host.endswith('.'+domain)
    except ValueError:return False
def supplier_for(market,source,url=''):
    sellers=CAT['suppliers'][market]
    for name,domain in sellers.items():
        if domain_is(url,domain): return name
    s=re.sub(r'[^a-z0-9]+',' ',str(source).lower()).strip()
    aliases={'Amazon US':['amazon','amazon com','amazon com marketplace'],'Amazon Mexico':['amazon mexico','amazon m x','amazon mx','amazon com mx','amazon mexico marketplace'],'Dell Refurbished':['dell refurbished','dellrefurbished com'],'B&H':['b h','b h photo video','b h photo video audio','bh photo'],'eBay':['ebay','ebay com','ebay com mx'],'Cyberpuerta':['cyberpuerta','cyberpuerta mx'],'PCEL':['pcel','pcel com']}
    for name in sellers:
        if s in aliases.get(name,[]): return name
    return None
def money_label(text,market,number=None):
    s=str(text or '').strip()
    if re.search(r'\b(?:CAD|AUD|EUR|GBP|JPY|COP|ARS)\b|[€£¥]|\b(?:from|starting at|desde|a partir de|monthly|mensual|installments|meses)\b',s,re.I): return None
    if re.search(r'\d\s*(?:[-–]|to|a)\s*\$?\s*\d',s,re.I): return None
    cur='MXN' if re.search(r'\bMXN\b|MX\s*\$|M\.N\.',s,re.I) else 'USD' if re.search(r'\bUSD\b|US\s*\$',s,re.I) else None
    if cur and cur!=MARKETS[market][0]: return None
    # Shopping structured price may be local but an unqualified dollar sign is not proof.
    if not cur and '$' not in s: return None
    if number is not None: return dec(number)
    m=re.fullmatch(r'\s*(?:MXN|USD|MX|US)?\s*\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d{1,2}))?\s*(?:MXN|USD|M\.N\.)?\s*',s,re.I)
    if not m:return None
    return dec(m.group(1).replace(',','')+'.'+(m.group(2) or '0'))
def row(market,part,seller,title,url,price=None,shipping=None,condition='',origin='search',variant=False,notes=''):
    return {'market':market,'part':part['id'],'supplier':seller,'title':str(title)[:300],'url':safe_url(url),'currency':MARKETS[market][0],
      'price':str(price) if price is not None else None,'shipping':str(shipping) if shipping is not None else None,
      'condition':str(condition)[:120],'origin':origin,'variant':bool(variant),'notes':str(notes)[:400]}
def screen(part,r,profile):
    t=r['title'].upper()
    condition=r['condition'].strip().upper()
    if re.search(r'\b(?:CADDY|TRAY|BRACKET|CABLE|ADAPTER|POWER SUPPLY|ENCLOSURE|DOCK|EMPTY|FOR PARTS|NOT WORKING|BARE[B ]?BONE|CASE ONLY|REPLACEMENT|SOPORTE|GABINETE VAC[IÍ]O)\b',t):
        return 'reject','Accessory, bare system or defective listing'
    if r['variant'] or re.search(r'\b(?:CHOOSE|SELECT|YOUR CHOICE|VARIATION|ELIGE|A ELEGIR)\b',t):
        return 'review','Variable listing: exact option and price required'
    if part['kind']=='drive':
        if re.search(r'^(?:(?:\d+\s*(?:PC|PCS|PIECE|PIECES|UNITS?)|NEW)\s+)*FOR\b|\b(?:COMPATIBLE WITH|REPLACEMENT FOR|OEM EQUIVALENT|GENERIC|SIN MARCA)\b',t):
            return 'review','Compatibility-style wording; genuine manufacturer identity not established'
        models=[m for m in part['models'] if re.search(r'(?<![A-Z0-9])'+re.escape(m)+r'(?![A-Z0-9])',t)]
        if not models: return 'review','Exact approved NAS drive model not established'
        if re.search(r'\b(?:USED|RENEWED|REFURBISHED|RECERTIFIED|REMANUFACTURED|PULL|REACONDICIONADO|USADO)\b',t+' '+r['condition'].upper()):
            return 'reject','Customer data drive must be new'
        if condition not in ('NEW','NUEVO','BRAND NEW','NEWCONDITION'):
            return 'review','Explicit new seller condition not established; title alone is insufficient'
        if re.search(r'\b(?:LOT|PACK|BUNDLE|2X|2 X|2-PACK|LOTE)\b',t):
            return 'review','Confirm per-drive price and pack count'
        return 'candidate','Exact model and new condition indicated; verify warranty, stock, seller, quantity'
    if re.search(r'\b(?:MICRO|MINI PC|SFF|SMALL FORM FACTOR)\b',t): return 'reject','Not the target tower form factor'
    if not re.search(r'\b(?:7060|7070|7080)\b',t) or 'OPTIPLEX' not in t or not re.search(r'\b(?:TOWER|MT|MINI TOWER|TORRE)\b',t):
        return 'review','Exact tower model/form factor not established'
    ram=part.get('ram',32 if profile=='plus' else 16)
    if not re.search(r'\b'+str(ram)+r'\s*(?:GB|G)\b',t) or not re.search(r'\b(?:I5|I7)\b',t) or not re.search(r'\b(?:240|250|256|480|500|512|960|1000|1024)\s*(?:GB|G)\b|\b1\s*TB\b',t) or not re.search(r'\b(?:SSD|NVME|M\.2)\b',t):
        return 'review','CPU/RAM/SSD configuration not established'
    return 'candidate','Check physical SATA bays, PSU connectors, cooling, RAM, SSD and warranty'
def import_verified(path,parts,target,fx):
    """Only manually confirmed, exact listings may produce a final landed BOM."""
    out=[]
    if not path:return out
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        for i,x in enumerate(csv.DictReader(f),2):
            if x.get('confirmed','').strip().lower()!='yes':continue
            part=next((p for p in parts if p['id']==x.get('part')),None)
            source=x.get('market');cur=MARKETS.get(source,(None,))[0]
            url=safe_url(x.get('url'));seller=x.get('supplier')
            if not part or source not in MARKETS or seller not in CAT['suppliers'][source] or not domain_is(url,CAT['suppliers'][source][seller]):
                raise ValueError('Invalid part/market/supplier/link at CSV row '+str(i))
            amounts=[dec(x.get(k)) for k in ('unit_price','unit_shipping','unit_tax','unit_import')]
            if any(v is None for v in amounts) or amounts[0]<=0:raise ValueError('Enter all four nonnegative landed-cost fields at row '+str(i))
            if x.get('currency')!=cur:raise ValueError('Currency mismatch at row '+str(i))
            if not x.get('exact_model') or not x.get('warranty') or x.get('compatibility_checked','').lower()!='yes':
                raise ValueError('Exact model, warranty and compatibility confirmation required at row '+str(i))
            if part['kind']=='drive' and (x.get('exact_model','').upper() not in part['models'] or x.get('condition','').lower()!='new'):
                raise ValueError('Drive must be exact approved model and new at row '+str(i))
            if int(x.get('available_quantity') or 0)<part['quantity']:raise ValueError('Insufficient confirmed quantity at row '+str(i))
            stamp=dt.date.fromisoformat(x['checked_date']);age=(dt.date.today()-stamp).days
            if not 0<=age<=3:raise ValueError('Confirmation must be dated within 3 days at row '+str(i))
            factor=Decimal(1)
            if source!=target:
                if fx is None or fx<=0:raise ValueError('Cross-market confirmed offers need explicit MXN per USD rate')
                factor=fx if target=='MX' else 1/fx
            total=sum(amounts)*factor*part['quantity']
            out.append({'part':part['id'],'supplier':seller,'title':x['exact_model'],'url':url,'market':source,'currency':MARKETS[target][0],'quantity':part['quantity'],'landed':str(total.quantize(Decimal('.01'))),'warranty':x['warranty'],'date':str(stamp)})
    return out
def choose(parts,rows):
    chosen=[]
    for p in parts:
        eligible=[r for r in rows if r['part']==p['id']]
        if not eligible:return []
        chosen.append(min(eligible,key=lambda r:Decimal(r['landed'])))
    return chosen
def output_path(s):
    p=Path(s).expanduser().resolve()
    if p==REPO or REPO in p.parents:raise ValueError('Keep reports and confirmed prices outside public Git repository')
    return p
def report(path,profile,target,rows,status,confirmed,bom,requests,markets):
    def esc(x):return html.escape(str(x if x is not None else 'Unknown'),quote=True)
    def link(r):
        url=safe_url(r.get('url'))
        return '<a target="_blank" rel="noopener noreferrer" href="'+esc(url)+'">Listing</a>' if url else 'No link'
    h=['<!doctype html><html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Jobbi sourcing</title><style>body{font:15px system-ui;background:#f7f6f2;color:#22352b;margin:0;padding:20px}main{max-width:1400px;margin:auto}table{border-collapse:collapse;width:100%;background:white}th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}a{color:#176b45}section{overflow:auto;margin-bottom:24px}small{color:#526257}</style><main><h1>JobbiSoft hardware sourcing</h1>']
    h.append('<p>'+esc(CAT['profiles'][profile]['name'])+' · target '+esc(target)+' · '+esc(dt.datetime.now(dt.timezone.utc).isoformat())+'</p><p>Search prices are leads, not checkout totals. No stock, warranty, compatibility or purchase is guaranteed. Authorized retailer searches: '+str(requests)+'</p>')
    h.append('<h2>Recommended confirmed bill of materials</h2>')
    if bom:
        h.append('<p><b>'+esc(MARKETS[target][0])+' '+esc(sum(Decimal(x['landed']) for x in bom))+'</b> verified-input landed subtotal, before labor and warranty reserve.</p><ul>')
        for x in bom:h.append('<li>'+esc(x['part'])+' × '+esc(x['quantity'])+' — '+esc(x['title'])+' — '+esc(x['supplier'])+' — '+esc(x['landed'])+' — '+link(x)+'</li>')
        h.append('</ul>')
    else:h.append('<p>No complete confirmed build yet. Fill the verification CSV with exact models, available quantity, shipping, tax, import and warranty. Do not buy based on search prices alone.</p>')
    h.append('<h2>Lowest screened advertised prices by market</h2><p>Only candidate listings with prices. This is a provisional price-only comparison, not a recommendation to purchase. Unknown delivery, taxes and availability are excluded; no cross-currency ranking.</p><section><table><thead><tr><th>Market / part</th><th>Lowest advertised candidate</th><th>Quantity</th><th>Advertised subtotal</th><th>Shipping per unit</th></tr></thead><tbody>')
    for m in MARKETS:
        for p in CAT['profiles'][profile]['parts']:
            matches=[r for r in rows if r['market']==m and r['part']==p['id'] and r['decision']=='candidate' and r['price'] is not None]
            if not matches:
                h.append('<tr><td>'+esc(m+' / '+p['id'])+'</td><td colspan="4">No screened priced offer</td></tr>')
                continue
            r=min(matches,key=lambda a:Decimal(a['price']))
            h.append('<tr><td>'+esc(m+' / '+p['id'])+'</td><td>'+esc(r['supplier'])+' — '+esc(r['title'])+' — '+link(r)+'</td><td>'+esc(p['quantity'])+'</td><td>'+esc(r['currency'])+' '+esc(Decimal(r['price'])*p['quantity'])+'</td><td>'+esc(r['shipping'])+'</td></tr>')
    h.append('</tbody></table></section><h2>Supplier coverage</h2><ul>')
    for x in status:h.append('<li>'+esc(' | '.join(x))+'</li>')
    h.append('</ul><h2>Supplier searches — all in one report</h2><p>Open a prepared search if no automated offer was returned. These links do not assert current stock or price.</p><ul>')
    for m in markets:
        for p in CAT['profiles'][profile]['parts']:
            for seller,domain in CAT['suppliers'][m].items():
                for query in p.get('models') or [p['query']]:
                    direct,indexed=links(m,seller,query,domain)
                    h.append('<li>'+esc(m+' / '+p['id']+' / '+seller+' / '+query)+' — <a href="'+esc(direct)+'" target="_blank" rel="noopener noreferrer">Supplier</a> · <a href="'+esc(indexed)+'" target="_blank" rel="noopener noreferrer">Site search</a></li>')
    h.append('</ul><h2>Search leads by market and part</h2><section><table><thead><tr><th>Market / part</th><th>Supplier / listing</th><th>Advertised price</th><th>Shipping</th><th>Screen</th><th>Notes</th></tr></thead><tbody>')
    for r in rows:
        h.append('<tr><td>'+esc(r['market']+' / '+r['part'])+'</td><td>'+esc(r['supplier'])+'<br>'+esc(r['title'])+'<br>'+link(r)+'</td><td>'+esc(r['currency'])+' '+esc(r['price'])+'</td><td>'+esc(r['shipping'])+'</td><td>'+esc(r['decision'])+'</td><td>'+esc(r['reason'])+'<br><small>'+esc(r['notes'])+'</small></td></tr>')
    h.append('</tbody></table></section><p>Only explicit manually confirmed offers are eligible for the final recommendation; choose the two drives from the same confirmed listing with sufficient quantity.</p></main></html>')
    path.write_text(''.join(h),encoding='utf-8')
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--profile',choices=CAT['profiles'],default='family')
    p.add_argument('--markets',choices=('US','MX','both'),default='both')
    p.add_argument('--target',choices=MARKETS,default='US')
    p.add_argument('--output',default='~/.local/share/jobbi-business/sourcing')
    p.add_argument('--postal-us',default='79901')
    p.add_argument('--deep',action='store_true',help='Legacy flag: all supplier links are always prepared')
    p.add_argument('--env-file',default='~/.config/jobbi-business/sourcing.env')
    p.add_argument('--dealcompare',default='~/.local/share/jobbi-business/dealcompare')
    p.add_argument('--allow-ebay-html',action='store_true',help='Only when authorized; use DealCompare HTML if no API credentials')
    p.add_argument('--authorized-retailer',action='append',default=[],help='Exact supplier name; explicitly confirm automated public collection is permitted; robots checks also apply')
    p.add_argument('--max-searches',type=int,default=24,help='Cap on optional retailer page requests')
    p.add_argument('--verified-csv',type=Path)
    p.add_argument('--fx',type=Decimal,help='Explicit MXN per USD for confirmed cross-border landed comparisons')
    p.add_argument('--offline',action='store_true',help='No network, only verified CSV')
    a=p.parse_args()
    if not 0<=a.max_searches<=100 or not re.fullmatch(r'\d{5}',a.postal_us):p.error('Invalid request cap or US postal code')
    if a.fx is not None and (not a.fx.is_finite() or a.fx<=0):p.error('Invalid FX')
    os.umask(0o077)
    try:
        out=output_path(a.output);out.mkdir(parents=True,exist_ok=True,mode=0o700)
        parts=CAT['profiles'][a.profile]['parts'];markets=list(MARKETS) if a.markets=='both' else [a.markets]
        verified=import_verified(a.verified_csv,parts,a.target,a.fx)
        rows=[];status=[];jobs=[];calls=0
        if not a.offline:
            load_env(a.env_file)
            try:
                api,engine=connect(a.dealcompare)
                if 'US' in markets:
                    for part in parts:
                        items,notes=deal_search(engine,api,part,a.allow_ebay_html)
                        for x in items:
                            if x.currency!='USD' or not domain_is(x.url,'ebay.com'):continue
                            price=dec(x.price)
                            if price is None or price<=0:continue
                            rows.append(row('US',part,'eBay',x.title,x.url,price,dec(x.shipping),x.condition,'DealCompare '+('Browse API' if api.configured() else 'authorized HTML'),x.price_is_starting,'Delivery not verified for your postal code; confirm seller, shipping, fixed price and stock.'))
                        status.append(('US',part['id'],'DealCompare eBay',str(len(items))+' leads; '+'; '.join(notes)))
                        if any('rate limit' in n.lower() or 'denied access' in n.lower() or 'paused' in n.lower() or 'challenge' in n.lower() for n in notes):break
                if 'MX' in markets:status.append(('MX','eBay','No direct Mexican marketplace API; prepared links and confirmed offers only'))
            except (ImportError,OSError,ValueError,subprocess.CalledProcessError) as e:
                status.append(('DealCompare','Unavailable: '+type(e).__name__+'; run setup script and use its virtualenv'))
            blocked=set()
            for m in markets:
                for seller,domain in CAT['suppliers'][m].items():
                    if seller=='eBay':continue
                    if seller not in a.authorized_retailer:
                        status.append((m,seller,'Prepared searches only; no authorized automatic provider'))
                        continue
                    for part in parts:
                        if seller in blocked or calls>=a.max_searches:break
                        for query in part.get('models') or [part['query']]:
                            if calls>=a.max_searches or seller in blocked:break
                            calls+=1
                            offers,state=collect(m,seller,query,domain,MARKETS[m][0])
                            for x in offers:rows.append(row(m,part,seller,x['title'],x['url'],x['price'],None,x['condition'],'Authorized public structured data',x['variant'],'Verify checkout, stock and warranty.'))
                            status.append((m,seller,part['id'],state,str(len(offers))+' leads'))
                            if state!='ok':blocked.add(seller)
        else:status.append(('Offline mode','No live search'))
        seen=set();unique=[]
        for r in rows:
            # eBay search tracking parameters vary by query; use the actual listing ID.
            item=re.search(r'/itm/(?:[^/]+/)?(\d{8,})(?:/|$)',u.urlsplit(r['url']).path) if r['supplier']=='eBay' else None
            k=(r['market'],r['part'],r['supplier'],item.group(1) if item else r['url'],r['price'])
            if k in seen:continue
            seen.add(k);part=next(x for x in parts if x['id']==r['part'])
            r['decision'],r['reason']=screen(part,r,a.profile);unique.append(r)
        unique.sort(key=lambda r:(r['market'],r['part'],{'candidate':0,'review':1,'reject':2}[r['decision']],Decimal(r['price']) if r['price'] is not None else Decimal('Infinity')))
        bom=choose(parts,verified)
        stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        dest=out/(a.profile+'-'+stamp);dest.mkdir()
        (dest/'offers.json').write_text(json.dumps({'offers':unique,'coverage':status,'verified':verified,'bom':bom},indent=2),encoding='utf-8')
        report(dest/'report.html',a.profile,a.target,unique,status,verified,bom,calls,markets)
        # Prepare an editable shortlist with no fabricated confirmations or costs.
        fields=(ROOT/'verified.example.csv').read_text().strip().split(',')
        with (dest/'review.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
            for r in unique:
                if r['decision']=='reject' or not domain_is(r['url'],CAT['suppliers'][r['market']][r['supplier']]):continue
                # Leave all landed prices blank; indexed prices are not checkout prices.
                writer.writerow({'part':r['part'],'market':r['market'],'supplier':r['supplier'],'url':r['url'],'currency':r['currency'],'confirmed':'no','compatibility_checked':'no'})
        print('Report:',dest/'report.html');print('Search leads:',len(unique),'| Complete confirmed build:',bool(bom),'| Authorized retailer searches:',calls)
        for m in markets:
            for part in parts:
                group=[r for r in unique if r['market']==m and r['part']==part['id']]
                print(m,part['id'],':',', '.join(f'{key}={sum(r["decision"]==key for r in group)}' for key in ('candidate','review','reject')))
        for entry in status:
            if 'DealCompare' in ' '.join(entry):print(' | '.join(entry))
        if not unique and not bom:print('No offers retrieved. See supplier search links, configure eBay or add confirmed quotes; no prices fabricated.')
    except (OSError,ValueError,KeyError,TypeError,InvalidOperation) as e:p.exit(1,'Error: '+str(e)+'\n')
if __name__=='__main__': main()
