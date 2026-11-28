"""Generate customer documents in memory from private ledger records."""
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape

TITLES={'quote':('Quotation','Cotización'),'receipt':('Cash receipt','Recibo de efectivo'),
        'acceptance':('Installation acceptance report','Informe de aceptación de instalación'),
        'handoff':('Customer handoff','Entrega al cliente')}

def render(order,plan,kind,lang,transaction,handoff):
    if kind not in TITLES or lang not in ('en','es'):
        raise ValueError('Unknown document or language')
    try:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer
    except ImportError:
        raise ValueError('Install python3-reportlab on the private dashboard host')
    es=lang=='es'
    def t(en,sp):return sp if es else en
    currency='MXN' if order['market']=='MX' else 'USD'
    def amount(cents):return f'{currency} {cents/100:,.2f}'
    title=TITLES[kind][int(es)]
    buf=BytesIO()
    doc=SimpleDocTemplate(buf,pagesize=letter,title=title,author='JobbiSoft',topMargin=64,bottomMargin=58)
    styles=getSampleStyleSheet()
    styles['Title'].alignment=0
    styles['Title'].textColor=HexColor('#163f49')
    story=[]
    def line(text,style='BodyText'):
        story.append(Paragraph(escape(str(text)),styles[style]))
    line('JobbiSoft Home','Heading3')
    line(title,'Title')
    line(t('Order','Folio')+' '+order['id']+'  |  '+date.today().isoformat())
    if order.get('label'):line(order['label'])
    story.append(Spacer(1,18))
    if kind=='receipt':
        row=next((r for r in order['transactions'] if r['id']==transaction),None)
        if row is None:raise ValueError('Choose a cash transaction recorded for this order')
        terms={'deposit':t('Cash deposit','Anticipo en efectivo'),'balance':t('Cash payment','Pago en efectivo'),'refund':t('Cash refund','Reembolso en efectivo')}
        line(terms[row['kind']],'Heading2')
        line(amount(row['amount']),'Title')
        line(t('Transaction','Transacción')+' '+row['id']+'  |  '+row['recorded'])
        line(t('Cash ledger receipt.','Comprobante del registro de efectivo.'))
    elif kind=='handoff':
        for item in handoff(order,plan,lang).splitlines()[2:]:
            if item:line(item)
    elif kind=='quote':
        line(t('Quoted one-time price','Precio cotizado de pago único'),'Heading2')
        line(amount(order['total']),'Title')
        if plan:
            line(f"{plan['tb']} TB  |  {plan['ram']} GB RAM")
            line(t('Requested applications','Aplicaciones solicitadas')+' · '+', '.join(plan['apps']))
        line(t('Payment in cash. Maintenance is optional. Confirm equipment, availability and written component warranty before accepting.',
               'Pago en efectivo. El mantenimiento es opcional. Confirme equipo, disponibilidad y garantía escrita por componente antes de aceptar.'))
        for part in order.get('components',[]):
            line(part['component']+' · '+part['provider']+' · '+part['expires'])
    else:
        for event in order.get('installation_events',[]):
            line(' · '.join([event['recorded'],event['step'],event['result'],event['note']]))
        line(t('Record actual results at delivery','Registre los resultados reales en la entrega'),'Heading2')
        for item in (t('Hardware and storage','Equipo y almacenamiento'),t('Private HTTPS and accounts','HTTPS privado y cuentas'),t('Application checks','Pruebas de aplicaciones'),t('Independent backup and restore','Respaldo independiente y restauración'),t('Restart and access','Reinicio y acceso')):
            line(item+'   ______________________________________')
            story.append(Spacer(1,10))
        line(t('Open issues','Pendientes')+'   ______________________________________')
        story.append(Spacer(1,20))
        line(t('Customer / technician signatures and date','Firmas de cliente y técnico y fecha'))
        line('_______________________      _______________________')
    def footer(canvas,doc):
        canvas.setFont('Helvetica',9)
        canvas.drawString(72,36,'JobbiSoft Home  |  '+order['id'])
        canvas.drawRightString(letter[0]-72,36,str(doc.page))
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()
