'use strict';
const $=id=>document.getElementById(id);let es=false,token='',state,selected,busy=false,current='',failedApps=[];const tr=(en,sp)=>es?sp:en;
const names={all:'All supported accounts',music:'Jobbi Music',movies:'StreamHub',photos:'Immich',files:'Nextcloud',tasks:'Vikunja',monitor:'Uptime Kuma',passwords:'Vaultwarden'};
async function api(path,data){const r=await fetch('/api/'+path,{method:data===undefined?'GET':'POST',headers:{Authorization:'Bearer '+token,...(data===undefined?{}:{'Content-Type':'application/json','X-Jobbi-Setup':'1'})},...(data===undefined?{}:{body:JSON.stringify(data)})});if(!r.ok){const err=Error('setup');err.httpStatus=r.status;throw err;}return r.json()}
function text(id,en,sp){$(id).textContent=tr(en,sp)}
function clearPassword(){$('password').value='';$('confirm').value=''}
function render(){
 document.documentElement.lang=es?'es':'en';text('lang','Español','English');text('title','Set up your home','Configura tu hogar');text('lead','One private session. Your accounts stay on your server.','Una sesión privada. Tus cuentas permanecen en tu servidor.');text('unlockTitle','Unlock setup','Desbloquear configuración');text('codeLabel','Setup code','Código de configuración');text('unlockButton','Continue','Continuar');text('usernameLabel','Owner username','Usuario propietario');text('emailLabel','Owner email','Correo del propietario');text('passwordLabel','New or existing password','Contraseña nueva o existente');text('confirmLabel','Confirm password','Confirma contraseña');text('finish',state?.lan?'Finish and open home':'Close setup session',state?.lan?'Finalizar y abrir inicio':'Cerrar sesión de configuración');text('nextNote','After setup, finish native encryption, private access and actual application tests with your technician.','Después, termina el cifrado nativo, acceso privado y pruebas reales con tu técnico.');
 if(!state)return;renderOptions();$('progress').max=state.apps.length||1;$('progress').value=state.done.length;$('progressText').textContent=state.done.length+' / '+state.apps.length+' '+tr('account steps completed','pasos de cuenta completados')+(current?' · '+tr('Configuring ','Configurando ')+names[current]+'…':'');
 $('steps').replaceChildren();for(const app of [...(state.apps.some(a=>a!=='passwords'&&!state.done.includes(a))?['all']:[]),...state.apps]){const b=document.createElement('button');b.type='button';b.textContent=(state.done.includes(app)?'✓ ':'')+(app==='all'?tr('Set up all','Configurar todas'):names[app]);b.disabled=busy||state.done.includes(app);b.setAttribute('aria-current',app===selected?'step':'false');b.onclick=()=>{selected=app;clearPassword();render()};$('steps').append(b)}
 $('finish').disabled=busy||(state.lan&&state.done.length!==state.apps.length);for(const id of ['email','password','confirm'])$(id).disabled=busy;$('accountForm').hidden=!selected||state.done.includes(selected);if($('accountForm').hidden)return;
 $('appTitle').textContent=names[selected];const vault=selected==='passwords';$('passwordFields').hidden=vault;for(const id of ['password','confirm'])$(id).required=!vault;
 $('username').disabled=busy||selected==='music';if(selected==='music')$('username').value=state.music_username;
 if(selected==='all'){text('createButton','Create / verify all accounts','Crear / verificar todas las cuentas');text('appHelp','One password for supported apps; unique passwords are safer. Music uses the configured username '+state.music_username+'. Existing accounts are not reset. Vaultwarden remains separate.','Una contraseña para las aplicaciones compatibles; se recomiendan contraseñas únicas. Música usa '+state.music_username+'. No se restablecen cuentas existentes. Vaultwarden es separado.');$('createButton').disabled=busy;return;}
 text('createButton',vault?'Invite owner':'Verify account',vault?'Invitar propietario':'Verificar cuenta');text('appHelp',vault?'Create your master password only in the native encrypted client.':'If the account already exists, enter its current password. Setup does not intentionally reset it.',vault?'Crea tu contraseña maestra solo en el cliente cifrado nativo.':'Si ya existe la cuenta, usa su contraseña actual. No se restablece intencionalmente.');
 $('createButton').disabled=busy;
}
function renderOptions(){
 const visible=state?.lan&&state.done.length===state.apps.length;$('optional').hidden=!visible;if(!visible)return;
 text('optionalTitle','Optional services','Servicios opcionales');text('dnsPasswordLabel','Separate Pi-hole admin password (12+ letters, numbers or ._!@%+-)','Contraseña independiente de Pi-hole (12+ letras, números o ._!@%+-)');text('consentText','I authorize these services and will download or share only content I have permission to use.','Autorizo estos servicios y solo descargaré o compartiré contenido permitido.');text('activateOptions','Activate selected services','Activar servicios seleccionados');text('connectTailnet','Connect my own account','Conectar mi propia cuenta');text('refreshTailnet','Refresh connection','Actualizar conexión');text('tailnetLink','Authorize Tailscale','Autorizar Tailscale');
 const options=state.options||{};for(const [id,key] of [['optSoulseek','soulseek'],['optInvidious','invidious'],['optDns','dns']]){const e=$(id);if(options[key])e.checked=false;e.disabled=busy||!!options[key]||(!state.apps.includes('music')&&key!=='dns')}
 $('dnsPasswordRow').hidden=!$('optDns').checked;$('dnsPassword').required=$('optDns').checked;$('dnsPassword').disabled=busy;
 $('activateOptions').disabled=busy;$('optConsent').disabled=busy;$('recheckOptions').disabled=busy||!Object.keys(options).length;text('recheckOptions','Recheck installed services','Volver a comprobar servicios');
 $('optionalStatus').textContent=Object.entries(options).map(([k,v])=>k+': '+tr({ready:'service probe passed',review:'needs review',starting:'starting'}[v]||v,{ready:'prueba aprobada',review:'requiere revisión',starting:'iniciando'}[v]||v)).join(' · ');
 const t=state.tailnet||{};$('tailnetText').textContent=tr('Connection: ','Conexión: ')+(t.state||'Unavailable')+'. '+tr('Enrollment uses your own account. Review private route access before enabling.','La inscripción usa tu cuenta. Revisa el acceso antes de activarlo.');
 $('connectTailnet').disabled=busy||['Running','Unavailable','NeedsMachineAuth'].includes(t.state);$('refreshTailnet').disabled=busy;
 const link=$('tailnetLink');link.hidden=!t.url;if(t.url)link.href=t.url;else link.removeAttribute('href');
 const eligible=t.state==='Running'&&!!t.host&&Object.values(options).every(v=>v==='ready');$('tailnetFinish').hidden=!eligible;
 $('tailnetHost').textContent=t.host||'';text('tailnetConsentText','I own this tailnet, enabled HTTPS certificates, reviewed device access policy and approve private app routes. This disables Vaultwarden administration after invitation.','Soy propietario de esta red, activé certificados HTTPS, revisé permisos de dispositivos y autorizo rutas privadas. Esto desactiva la administración de Vaultwarden tras la invitación.');text('finishTailnetButton','Finish using private Tailscale HTTPS','Finalizar con HTTPS privado de Tailscale');$('tailnetConsent').disabled=busy;$('finishTailnetButton').disabled=busy||!eligible||!$('tailnetConsent').checked
}
$('optDns').onchange=()=>renderOptions();
$('optionalForm').onsubmit=async e=>{e.preventDefault();if(busy)return;const services=[['optSoulseek','soulseek'],['optInvidious','invidious'],['optDns','dns']].filter(([id])=>$(id).checked).map(([,key])=>key);if(!services.length||!$('optConsent').checked){text('status','Select services and authorize them.','Selecciona y autoriza los servicios.');return}const data={services,consent:true,dns_password:services.includes('dns')?$('dnsPassword').value:''};$('dnsPassword').value='';busy=true;render();text('status','Installing optional services. Keep this page open.','Instalando servicios opcionales. Mantén esta página abierta.');try{state=await api('options',data);text('status','Optional service results are shown above.','Los resultados aparecen arriba.')}catch{try{state=await api('status')}catch{}text('status','Optional setup interrupted. Existing accounts are retained.','Configuración interrumpida. Se conservan las cuentas.')}finally{data.dns_password='';busy=false;$('optConsent').checked=false;render()}};
$('recheckOptions').onclick=async()=>{if(busy)return;busy=true;render();try{state=await api('options-recheck',{});text('status','Existing service probes updated; no accounts changed.','Pruebas actualizadas; no se cambiaron cuentas.')}catch{text('status','Could not recheck services.','No se pudieron comprobar los servicios.')}finally{busy=false;render()}};
$('connectTailnet').onclick=async()=>{if(busy)return;busy=true;render();try{state=await api('tailnet',{consent:true})}catch{text('status','Tailscale enrollment unavailable.','Inscripción Tailscale no disponible.')}finally{busy=false;render()}};
$('tailnetConsent').onchange=()=>renderOptions();
$('finishTailnetButton').onclick=async()=>{if(busy||!$('tailnetConsent').checked)return;busy=true;render();text('status','Configuring private HTTPS routes. Keep the setup page open.','Configurando rutas HTTPS privadas. Mantén abierta esta página.');try{const result=await api('finish-tailnet',{consent:true,host:state.tailnet.host});token='';state=null;clearPassword();$('wizard').hidden=true;const link=$('finishedUrl');link.href=result.url;link.textContent=result.url;link.hidden=false;text('status','Private configuration complete. Open from an authorized Tailscale device; verify certificate and app access.','Configuración privada lista. Abre desde un dispositivo Tailscale autorizado; verifica certificado y aplicaciones.')}catch{text('status','Private setup failed or connection lost. Check the physical console. Do not repeat an unfinished transaction.','La configuración privada falló o se perdió la conexión. Revisa la consola física. No repitas una transacción incompleta.')}finally{busy=false;render()}};
$('refreshTailnet').onclick=async()=>{if(busy)return;try{state=await api('status');render()}catch{text('status','Connection interrupted.','Conexión interrumpida.')}};
$('lang').onclick=()=>{es=!es;render()};
$('unlockForm').onsubmit=async e=>{e.preventDefault();token=$('code').value;$('code').value='';try{state=await api('status');$('unlock').hidden=true;$('wizard').hidden=false;$('username').value=state.music_username||'owner';selected=state.apps.some(a=>a!=='passwords'&&!state.done.includes(a))?'all':state.apps.find(a=>!state.done.includes(a));$('status').textContent='';render()}catch{token='';text('status','Invalid or expired setup code.','Código inválido o vencido.')}};
$('accountForm').onsubmit=async e=>{
 e.preventDefault();if(busy)return;
 const data={username:$('username').value,email:$('email').value,password:$('password').value,confirm:$('confirm').value};
 if(selected!=='passwords'&&data.password!==data.confirm){text('status','Passwords do not match.','Las contraseñas no coinciden.');return}
 const queue=selected==='all'?state.apps.filter(a=>a!=='passwords'&&!state.done.includes(a)):[selected];
 busy=true;failedApps=[];clearPassword();render();
 try{
  for(const app of queue){
   current=app;render();text('status','Configuring '+names[app]+'…','Configurando '+names[app]+'…');
   try{
    state=await api('create',{...data,app});
   }catch(err){
    // A lost response does not prove failure. Reconcile with the authenticated server
    // before advancing. If even status is unavailable, stop and retain prior results.
    state=await api('status');
    if(!state.done.includes(app)){if(err.httpStatus!==400)throw err;failedApps.push(app);}
   }
   render();
  }
  selected=state.apps.find(a=>!state.done.includes(a));
  if(failedApps.length)$('status').textContent=tr('Needs individual review: ','Revisión individual: ')+failedApps.map(a=>names[a]).join(', ');
  else text('status','Account steps completed. Functional acceptance is still required.','Pasos de cuenta completados. Faltan las pruebas funcionales.');
 }catch{text('status','Connection interrupted. Check the server and reopen setup to reconcile existing accounts.','Conexión interrumpida. Revisa el servidor y vuelve a abrir la configuración.')}
 finally{data.password='';data.confirm='';current='';clearPassword();busy=false;render()}
};
$('finish').onclick=async()=>{if(busy)return;try{const result=await api('finish',{});token='';state=null;clearPassword();$('wizard').hidden=true;if(result.gateway){text('status','Setup finished. The private dashboard is starting. Reopen this same address once the console reports ready.','Configuración terminada. El panel privado está iniciando. Abre esta dirección cuando la consola indique que está listo.')}else text('status','Setup session closed.','Sesión cerrada.')}catch{text('status','Close the local setup process in the terminal.','Cierra el proceso local en la terminal.')}};
render();
