"""Paired owner setup for customer-authorized Prowlarr indexers."""
import hashlib,json,re,urllib.request,urllib.error
from pathlib import Path

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def client(i,env):
    if env.get('BIND_IP')!='127.0.0.1' or 'movies' not in env['COMPOSE_PROFILES'].split(','):
        raise ValueError('Require isolated movie service')
    port=int(env['PROWLARR_PORT']);key=env['PROWLARR_API_KEY']
    if not 1024<=port<=65535 or not re.fullmatch('[A-Za-z0-9]{24,128}',key):
        raise ValueError('Local API connection not ready')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    def call(path,data=None):
        if path not in ('/api/v1/indexer/schema','/api/v1/indexer','/api/v1/indexer/test'):
            raise ValueError('Unsupported API operation')
        req=urllib.request.Request('http://127.0.0.1:'+str(port)+path,
            data=None if data is None else json.dumps(data).encode(),
            headers={'X-Api-Key':key,'Accept':'application/json','Content-Type':'application/json'})
        try:
            with opener.open(req,timeout=45) as res:
                raw=res.read(8*1024*1024+1)
                if len(raw)>8*1024*1024:raise ValueError('Response too large')
                return json.loads(raw) if raw.strip() else None
        except (OSError,ValueError) as exc:
            raise ValueError('Local Prowlarr operation failed') from None
    return call

def identity(row):
    return hashlib.sha256(json.dumps([row.get(k,'') for k in ('implementation','definitionName','name')],ensure_ascii=True).encode()).hexdigest()[:32]

def catalog(call):
    rows=call('/api/v1/indexer/schema')
    if not isinstance(rows,list) or len(rows)>3000:raise ValueError('Invalid schema catalog')
    result={}
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get('name'),str) or not isinstance(row.get('implementation'),str):continue
        k=identity(row)
        if k in result:raise ValueError('Ambiguous indexer schema')
        result[k]=row
    return result

def editable(row):
    fields={}
    for f in row.get('fields',[]):
        name=f.get('name','');kind=f.get('type','')
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',name):continue
        if f.get('hidden') or kind not in ('textbox','password','number','checkbox','select','url','tag'):continue
        if kind=='tag':continue
        item={'name':name,'label':str(f.get('label') or name)[:160],'type':kind}
        if kind=='select':
            choices=[{'value':o['value'],'label':str(o.get('name',''))[:160]}
                     for o in f.get('selectOptions') or [] if isinstance(o,dict) and type(o.get('value')) in (str,int)]
            if not choices:continue
            item['choices']=choices[:100]
        fields[name]=item
    return fields

def handle(call,request):
    action=request.get('action')
    if action=='list' and set(request)=={'action'}:
        rows=catalog(call)
        existing=call('/api/v1/indexer')
        return {'templates':sorted([{'id':k,'name':v['name'][:160],'protocol':str(v.get('protocol',''))[:24]} for k,v in rows.items()],key=lambda x:x['name'].casefold()),
                'installed':[{'name':str(v.get('name',''))[:160],'enabled':v.get('enable') is True} for v in existing]}
    if action not in ('fields','add') or set(request)!=({'action','id'} if action=='fields' else {'action','id','name','values','consent'}):
        raise ValueError('Invalid indexer operation')
    row=catalog(call).get(request['id'])
    if row is None:raise ValueError('Unknown current indexer schema')
    fields=editable(row)
    if action=='fields':return {'fields':list(fields.values())}
    name=request['name'];values=request['values']
    if request['consent'] is not True or not isinstance(name,str) or not 1<=len(name.strip())<=100 or not isinstance(values,dict) or set(values)-set(fields):
        raise ValueError('Explicit authorized indexer configuration required')
    name=name.strip()
    if any(str(x.get('name','')).casefold()==name.casefold() for x in call('/api/v1/indexer')):
        raise ValueError('Indexer name already exists; no duplicate created')
    for key,v in values.items():
        field=fields[key];kind=field['type']
        if kind=='checkbox':
            valid=type(v) is bool
        elif kind=='number':
            valid=type(v) is int and abs(v)<=2147483647
        elif kind=='select':
            valid=any(type(v) is type(o['value']) and v==o['value'] for o in field['choices'])
        else:
            valid=isinstance(v,str) and len(v)<=1024 and not any(ord(c)<32 for c in v)
        if not valid:raise ValueError('Invalid indexer field')
    # Only an exact current vendor schema can be submitted; no caller-supplied
    # endpoints, API keys, implementation classes or arbitrary fields.
    payload={**row,'name':name,'enable':True}
    payload.pop('id',None)
    payload['fields']=[{**f,**({'value':values[f['name']]} if f.get('name') in values else {})} for f in row.get('fields',[])]
    call('/api/v1/indexer/test',payload)
    created=call('/api/v1/indexer',payload)
    if not isinstance(created,dict) or not isinstance(created.get('id'),int):
        raise ValueError('Creation not confirmed; refresh installed indexers before retry')
    return {'created':True,'name':name}
