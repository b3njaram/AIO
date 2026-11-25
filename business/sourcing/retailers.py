"""Optional retailer collection with explicit authorization and robots checks.
No login, proxy, CAPTCHA handling, browser spoofing or hidden API.
"""
import json,re,time,urllib.parse as u,urllib.request as req,urllib.robotparser as robots
from html.parser import HTMLParser
from decimal import Decimal
UA='JobbiSoftSourcing'
SEARCH={
 'Amazon US':'https://www.amazon.com/s?k={q}',
 'Amazon Mexico':'https://www.amazon.com.mx/s?k={q}',
 'Dell Refurbished':'https://www.dellrefurbished.com/',
 'B&H':'https://www.bhphotovideo.com/c/search?q={q}',
 'Cyberpuerta':'https://www.cyberpuerta.mx/index.php?cl=search&searchparam={q}',
 'PCEL':'https://pcel.com/index.php?route=product/search&search={q}',
 'eBay':'https://www.ebay.com/sch/i.html?_nkw={q}'
}
def links(market,supplier,query,domain):
    direct=SEARCH[supplier].replace('{q}',u.quote_plus(query))
    if market=='MX' and supplier=='eBay':direct=direct.replace('www.ebay.com/','www.ebay.com.mx/')
    indexed='https://www.google.com/search?'+u.urlencode({'q':query+' site:'+domain,'gl':market.lower()})
    return direct,indexed
class NoRedirect(req.HTTPRedirectHandler):
    def redirect_request(self,*a,**kw):return None
OPENER=req.build_opener(NoRedirect())
class LD(HTMLParser):
    def __init__(self):
        super().__init__();self.active=False;self.buf=[];self.docs=[]
    def handle_starttag(self,tag,attrs):
        if tag=='script' and dict(attrs).get('type','').lower()=='application/ld+json':self.active=True;self.buf=[]
    def handle_data(self,data):
        if self.active:self.buf.append(data)
    def handle_endtag(self,tag):
        if tag=='script' and self.active:
            self.active=False
            try:self.docs.append(json.loads(''.join(self.buf)))
            except (ValueError,RecursionError):pass
def products(markup,base,domain,currency):
    parser=LD();parser.feed(markup)
    def walk(node,depth=0):
        if depth>12:return
        if isinstance(node,list):
            for x in node[:300]:yield from walk(x,depth+1)
        elif isinstance(node,dict):
            typ=node.get('@type',[])
            if typ=='Product' or isinstance(typ,list) and 'Product' in typ:yield node
            for key in ('@graph','itemListElement','item','mainEntity','hasVariant'):
                if key in node:yield from walk(node[key],depth+1)
    out=[]
    for x in walk(parser.docs):
        title=x.get('name');offers=x.get('offers')
        if not isinstance(title,str) or not isinstance(offers,dict) or offers.get('@type')!='Offer':continue
        if offers.get('priceCurrency')!=currency or offers.get('availability','').split('/')[-1]!='InStock':continue
        try:
            price=Decimal(str(offers.get('price')))
            if not price.is_finite() or not 0<price<100000000:continue
            url=u.urljoin(base,offers.get('url') or x.get('url') or '')
            p=u.urlsplit(url)
            if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or not (p.hostname==domain or (p.hostname or '').endswith('.'+domain)) or url==base:continue
        except (ValueError,ArithmeticError,TypeError):continue
        condition=offers.get('itemCondition','').split('/')[-1]
        out.append({'title':title,'price':price,'url':url,'condition':{'NewCondition':'New','UsedCondition':'Used','RefurbishedCondition':'Refurbished'}.get(condition,''),'variant':bool(x.get('hasVariant') or x.get('isVariantOf'))})
    return out[:100]
def fetch(url):
    with OPENER.open(req.Request(url,headers={'User-Agent':UA,'Accept':'text/html,text/plain,application/xhtml+xml'}),timeout=15) as r:
        b=r.read(5_000_001)
        if len(b)>5_000_000:raise ValueError('response too large')
        return b.decode('utf-8',errors='replace')
def collect(market,supplier,query,domain,currency):
    """Call only after permission for this supplier has been confirmed."""
    url,_=links(market,supplier,query,domain)
    if '{q}' not in SEARCH[supplier]:return [],'no supported search route; use links'
    if supplier=='eBay':return [],'use DealCompare'
    p=u.urlsplit(url)
    try:
        rp=robots.RobotFileParser();rp.parse(fetch('https://'+p.netloc+'/robots.txt').splitlines())
        if not rp.can_fetch(UA,url):return [],'robots.txt disallows search'
        time.sleep(max(3,rp.crawl_delay(UA) or 0))
        markup=fetch(url)
        if re.search(r'<title[^>]*>[^<]*(?:captcha|access denied|just a moment|robot check)',markup,re.I) or re.search(r'id=["\'](?:captcha|challenge-form|px-captcha)',markup,re.I):
            return [],'access challenge; stop'
        rows=products(markup,url,domain,currency)
        return rows,'ok' if rows else 'no readable in-stock Product/Offer structured data'
    except (OSError,ValueError,TypeError) as e:return [],'unavailable: '+str(getattr(e,'code',type(e).__name__))
