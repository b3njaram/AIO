'use strict';
const spanish = new Map(`
Demo only · no login · use test records|Solo demo · sin acceso por contraseña · usa registros de prueba
Download diagnostic snapshot|Descargar diagnóstico
diagnostics_exported|Diagnóstico exportado
Customers|Clientes
Customer appliances|Servidores de clientes
Find appliance|Buscar servidor
Health filter|Filtrar salud
Refresh fleet|Actualizar servidores
Export visible summary|Exportar resumen visible
Recent activity|Actividad reciente
Reports are customer-shared snapshots, not proof of live connectivity.|Los informes son datos compartidos por clientes, no prueba de conexión en vivo.
Private fleet summary downloaded.|Resumen privado descargado.
registered|Registrado
sharing_allowed|Permiso concedido
sharing_revoked|Permiso revocado
report_imported|Informe recibido
reporting_enabled|Informes automáticos habilitados
reporting_revoked|Credencial revocada
Private registry · customer-shared reports only|Registro privado · solo informes compartidos por clientes
Register appliance|Registrar servidor
Appliance ID|ID del servidor
Appliance label|Nombre del servidor
Save appliance|Guardar servidor
Import shared report|Importar informe compartido
Appliance|Servidor
Customer health JSON|JSON de salud del cliente
Import report|Importar informe
Reports are manually provided, not live monitoring or proof of identity.|Los informes se entregan manualmente; no son monitoreo en vivo ni prueba de identidad.
Registered|Registrados
Reports need review|Informes por revisar
Sharing enabled|Uso compartido habilitado
No reported alerts|Sin alertas reportadas
Not shared|No compartido
No report|Sin informe
Stale report|Informe desactualizado
Needs review|Requiere revisión
Storage free|Espacio libre
Backup|Respaldo
Report date|Fecha del informe
Health details|Detalles de salud
Temperature|Temperatura
Alerts|Alertas
Release|Versión
Support ends|Fin del soporte
Warranty ends|Fin de garantía
Revoke sharing|Revocar permiso
Record customer consent|Registrar consentimiento
Revoke sharing and erase the stored health report?|¿Revocar el permiso y borrar el informe almacenado?
Confirm the customer explicitly agreed to share health reports.|Confirma que el cliente aceptó compartir informes de salud.
Automatic reporting enabled|Informes automáticos habilitados
Automatic reporting disabled|Informes automáticos deshabilitados
Reporting credential expires|Vencimiento de credencial
Revoke reporting credential|Revocar credencial
Issue reporting credential|Generar credencial
Revoke automatic reporting?|¿Revocar informes automáticos?
Confirm customer approved automatic private health reporting for 90 days.|Confirma que el cliente autorizó informes privados automáticos durante 90 días.
Copy this one-time credential securely. It will not be displayed again.|Copia esta credencial de forma segura. No se mostrará nuevamente.
No registered appliances.|Sin servidores registrados.
Appliance saved.|Servidor guardado.
Health report imported.|Informe de salud importado.
verified|Verificado
stale|Vencido
review|Revisar
mount_unavailable|Disco no disponible
not_verified|Sin verificar
healthy|Saludable
degraded|Degradado
syncing|Sincronizando
unknown|Desconocido
Overview|Resumen
WORKSPACE|ESPACIO DE TRABAJO
What needs your attention today?|¿Qué necesita tu atención hoy?
Quick actions|Acciones rápidas
Find and verify equipment|Busca y verifica equipo
Manage orders and payments|Administra pedidos y pagos
Plan customer servers|Planea servidores de clientes
Review open cases|Revisa casos abiertos
Generate customer PDFs|Genera documentos PDF
Upcoming renewals|Próximos vencimientos
Recent cash transactions|Movimientos de efectivo recientes
No cash transactions yet.|Aún no hay movimientos de efectivo.
Active orders|Pedidos activos
Installations in progress|Instalaciones en curso
Open support cases|Casos abiertos
Delivered|Entregados
Documents|Documentos
Verification requirements|Requisitos de verificación
Verify a purchase option|Verificar una oferta
Create or edit order|Crear o editar pedido
Warranty and payment terms|Condiciones de garantía y pago
Create installation plan|Crear plan de instalación
Installation log|Bitácora de instalación
Component warranties|Garantías por componente
Create or edit support case|Crear o editar caso
Plain text draft|Borrador de texto
Payment history and notes|Historial de pagos y notas
Screening details|Detalles de evaluación
JOBBISOFT / PRIVATE OPERATIONS|JOBBISOFT / OPERACIONES PRIVADAS
Business dashboard|Panel de administración
Cash only · Private|Solo efectivo · Privado
Hardware finder|Buscar equipo
Profitability|Rentabilidad
Orders & warranty|Pedidos y garantías
Installation|Instalación
Support & handoff|Soporte y entrega
Find compatible hardware|Buscar equipo compatible
Build|Configuración
Target market|Mercado de destino
Search markets|Mercados de búsqueda
Both|Ambos
Search hardware|Buscar equipo
Saved report|Informe guardado
Part|Componente
All|Todos
Computer|Computadora
Hard drive|Disco duro
Market|Mercado
Screen|Evaluación
candidate|candidato
review|revisar
reject|descartado
Find text|Buscar texto
Load eBay pictures (external)|Cargar imágenes de eBay (externas)
Show more|Mostrar más
Provider coverage and diagnostics|Cobertura y diagnóstico de proveedores
All supplier search links|Enlaces de búsqueda por proveedor
Confirmed purchase options|Opciones de compra verificadas
Check exact option, condition, seller, warranty, compatibility, quantity and all costs for the target market. Unknown is not zero. Only confirmed offers are ranked.|Verifica la variante exacta, condición, vendedor, garantía, compatibilidad, cantidad y costos en el mercado de destino. Un costo desconocido no es cero. Solo se comparan ofertas verificadas.
Actual MXN per USD (required across markets)|Tipo de cambio real en MXN por USD para comparar mercados
Drive|Disco
Source market|Mercado de origen
Supplier|Proveedor
Exact model|Modelo exacto
Condition|Condición
New|Nuevo
Refurbished|Reacondicionado
Used|Usado
Available quantity|Cantidad disponible
Listing URL|Enlace del anuncio
Unit price|Precio unitario
Unit shipping|Envío por unidad
Unit tax|Impuesto por unidad
Unit import|Importación por unidad
Warranty and region|Garantía y región
Checked date|Fecha de verificación
Exact compatibility checked|Compatibilidad exacta verificada
Verified current purchase price, condition, stock, shipping, tax, import and warranty|Verifiqué precio actual, condición, existencias, envío, impuestos, importación y garantía
Save confirmed offer|Guardar oferta verificada
Recalculate confirmed build|Recalcular configuración verificada
Use confirmed hardware cost in profitability|Usar el costo verificado para calcular rentabilidad
Price and contribution|Precio y contribución
Support months|Meses de soporte
Hardware (landed)|Equipo con costos de adquisición
Labor|Mano de obra
Support reserve|Reserva de soporte
Additional shipping / travel|Envío adicional o traslado
Warranty reserve|Reserva de garantía
Overhead|Gastos indirectos
Hardware markup %|Recargo sobre equipo %
Target contribution %|Contribución objetivo %
Calculate|Calcular
Cash-only, no payment processor fees. Pre-tax proposal; not an invoice. Enter costs not already included in landed hardware.|Pago en efectivo sin comisión de procesamiento. Propuesta antes de impuestos. Ingresa únicamente gastos adicionales al costo de adquisición.
Start order from calculated price|Crear pedido con el precio calculado
Orders and cash|Pedidos y efectivo
Order ID|Folio del pedido
Customer reference (optional)|Referencia del cliente (opcional)
Agreed total|Total acordado
Stage|Etapa
quoted|cotizado
accepted|aceptado
procurement|en compras
installing|en instalación
delivered|entregado
cancelled|cancelado
Delivery date|Fecha de entrega
Hardware condition|Condición del equipo
Customer owned|Propiedad del cliente
Private note (no secrets)|Nota privada (sin credenciales)
Save order|Guardar pedido
New order|Nuevo pedido
Record cash transaction|Registrar movimiento de efectivo
Order|Pedido
Transaction ID|Folio del movimiento
Type|Tipo
deposit|anticipo
balance|liquidación
refund|reembolso
Amount|Importe
Date|Fecha
Record cash|Registrar efectivo
Warranty dates are policy estimates; longer statutory or agreed coverage prevails. For mixed hardware, maintain item-specific warranty records. Refunds do not amend the original agreed total. Keep customer records private.|Las fechas de garantía son estimaciones. Prevalece la cobertura legal o acordada más amplia. Registra la garantía de cada componente. Los reembolsos conservan el total original acordado. Protege los registros del cliente.
Customer installation planner|Planificador de instalaciones
Prepare a plan for a dedicated customer server. This dashboard never executes Docker or SSH commands for customer installations.|Prepara un plan para el servidor dedicado del cliente. El técnico ejecuta los comandos en ese equipo.
Order (optional)|Pedido (opcional)
Instance name|Nombre de la instalación
Mounted data root|Ruta del almacenamiento montado
Independent backup path|Ruta del respaldo independiente
Base port|Puerto inicial
Storage TB|Almacenamiento en TB
Time zone|Zona horaria
Mirrored disks requested|Se solicitaron discos en espejo
Generate installation plan|Generar plan de instalación
Download plan|Descargar plan
Export USB profile|Exportar perfil USB
Support, warranty & maintenance|Soporte, garantías y mantenimiento
Case ID|Folio del caso
support|soporte
warranty|garantía
return|devolución
maintenance|mantenimiento
Subject|Asunto
Status|Estado
open|abierto
waiting|en espera
resolved|resuelto
Notes (no secrets)|Notas (sin credenciales)
Save case|Guardar caso
Clear|Limpiar
Customer handoff|Entrega al cliente
Language|Idioma
English|Inglés
Download handoff draft|Descargar borrador de entrega
Draft only: include actual tested service URLs, signed acceptance, item warranties and mandatory disclosures separately. Never include credentials.|Borrador. Adjunta las direcciones verificadas de los servicios, el acta firmada, las garantías y los avisos correspondientes. Entrega las credenciales por separado.
JobbiSoft · Owner-only · No purchases or external payments initiated|JobbiSoft · Acceso del propietario · Sin compras ni pagos externos
Choose saved report|Elegir informe guardado
No saved order|Sin pedido guardado
Edit|Editar
View plan|Ver plan
Remove|Quitar
Review / confirm|Revisar y confirmar
Supplier search|Buscar con el proveedor
Site search|Buscar en el sitio
Open listing|Abrir anuncio
Listing|Anuncio
All retrieved|Total encontrado
Proposed pre-tax price|Precio propuesto antes de impuestos
Estimated expenses|Gastos estimados
Contribution|Contribución
Minimum target price|Precio objetivo mínimo
Contribution margin|Margen de contribución
Edit order details|Editar datos del pedido
Confirmed offer saved.|Oferta verificada guardada.
Order saved.|Pedido guardado.
Case saved.|Caso guardado.
Cash recorded. Issue applicable receipt separately.|Efectivo registrado. Emite el recibo correspondiente.
Plan generated; review and execute only on the customer host.|Plan generado. Revísalo y ejecútalo únicamente en el servidor del cliente.
Draft downloaded. Attach actual acceptance and warranty terms.|Borrador descargado. Adjunta el acta de aceptación y las garantías.
Calculation complete; verify tax and final agreed amount.|Cálculo terminado. Verifica impuestos y total acordado.
No recorded expiry in the next 30 days.|Sin vencimientos registrados en los próximos 30 días.
No results for these filters. Check provider coverage and supplier searches.|No hay resultados con estos filtros. Revisa la cobertura y las búsquedas por proveedor.
No complete confirmed build for this profile and target.|Faltan ofertas verificadas para completar esta configuración en el mercado elegido.
`.trim().split('\n').map(line=>line.split('|')));
let uiLanguage=localStorage.getItem('jobbi-business-language')==='es'?'es':'en';
const translate=value=>uiLanguage==='es'?(spanish.get(value)??value):value;
const dashboardPicker=document.getElementById('dashboardLanguage');
dashboardPicker.value=uiLanguage;
document.documentElement.lang=uiLanguage;
const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
const labels=[];
while(walker.nextNode()){
  const node=walker.currentNode;
  const label=node.nodeValue.trim();
  if(!spanish.has(label))continue;
  if(node.parentElement.tagName==='OPTION'&&!node.parentElement.hasAttribute('value')){
    node.parentElement.value=label;
  }
  labels.push([node,node.nodeValue,label]);
}
function translateInterface(){
  document.documentElement.lang=uiLanguage;
  for(const [node,original,label] of labels)node.nodeValue=original.replace(label,translate(label));
}
translateInterface();
dashboardPicker.onchange=()=>{
  uiLanguage=dashboardPicker.value;
  localStorage.setItem('jobbi-business-language',uiLanguage);
  translateInterface();
  document.dispatchEvent(new Event('jobbi-language'));
};
