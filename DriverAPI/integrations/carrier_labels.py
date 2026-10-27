"""Local PDF/HTML test label renderer. Lazy ReportLab dependency; no network."""
import base64
from io import BytesIO
import html


def parcel_ids(tracking, count):
    return [tracking + '-' + str(i).zfill(3) for i in range(1, count + 1)]


def render_test_labels(payload, tracking, output_format='pdf'):
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF, renderSVG
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit

    ids=parcel_ids(tracking,len(payload['parcels']))
    target=payload['recipient']; loc=payload['destination']; sender=payload['sender']; origin=payload['origin']

    def qr(identifier, size):
        widget=QrCodeWidget(identifier); x0,y0,x1,y1=widget.getBounds()
        drawing=Drawing(size,size,transform=[size/(x1-x0),0,0,size/(y1-y0),0,0])
        drawing.add(widget)
        return drawing

    if output_format == 'html':
        sections=[]
        for i,identifier in enumerate(ids,1):
            svg=renderSVG.drawToString(qr(identifier,100))
            if isinstance(svg,str):svg=svg.encode()
            image=base64.b64encode(svg).decode()
            def esc(value):return html.escape(str(value),quote=True)
            sections.append('<section><h2>WAREX LOGISTICS</h2><strong>TEST ONLY - NOT FOR DELIVERY</strong>'
                +'<p>Parcel '+str(i)+' of '+str(len(ids))+'</p><img width="100" height="100" src="data:image/svg+xml;base64,'+image+'">'
                +'<p>'+esc(identifier)+'</p><h3>DELIVER TO</h3><p>'+esc(target['name'])+'<br>'+esc(target['address'])+'<br>'
                +esc(target.get('address2',''))+'<br>'+esc(loc['suburb']+' '+loc['state']+' '+loc['postcode'])+'</p>'
                +'<p>FROM: '+esc(sender['name']+', '+sender['address']+', '+origin['suburb']+' '+origin['postcode'])+'</p>'
                +'<p>STANDARD | '+esc(payload['parcels'][i-1]['actual_weight_kg'])+' kg actual</p>'
                +'<p>'+esc(payload.get('instructions',''))+'</p></section>')
        return ('<!doctype html><html><head><meta charset="utf-8"><title>Warex test labels</title><style>'
                '@page{size:4in 6in;margin:0}body{margin:0;font-family:Arial,sans-serif;font-size:10px}'
                'section{box-sizing:border-box;width:4in;min-height:6in;padding:16px;break-after:page;overflow-wrap:anywhere}'
                'strong{color:#900}h2{margin:0}p{margin:8px 0}</style></head><body>'+''.join(sections)+'</body></html>').encode()
    if output_format != 'pdf':
        raise ValueError('Supported label formats are pdf and html.')
    output=BytesIO(); pdf=canvas.Canvas(output,pagesize=(288,432),pageCompression=1)
    pdf.setTitle('Warex Test Parcel Labels');pdf.setAuthor('Warex Logistics')
    def text_box(text,x,y,width,height,size=10):
        while size >= 6:
            lines=simpleSplit(text,'Helvetica',size,width)
            if len(lines)*(size+2) <= height and all(pdf.stringWidth(line,'Helvetica',size)<=width for line in lines):
                pdf.setFont('Helvetica',size)
                for line in lines:pdf.drawString(x,y,line);y-=size+2
                return
            size-=1
        raise ValueError('Label text is too long for the 4x6 PDF; shorten the supplied fields.')
    for i,identifier in enumerate(ids,1):
        pdf.setFont('Helvetica-Bold',16);pdf.drawString(16,407,'WAREX LOGISTICS')
        pdf.setFont('Helvetica-Bold',10);pdf.drawString(16,388,'TEST ONLY - NOT FOR DELIVERY')
        pdf.setFont('Helvetica',9);pdf.drawString(16,371,'Parcel %s of %s | STANDARD' % (i,len(ids)))
        renderPDF.draw(qr(identifier,90),pdf,99,272)
        text_box(identifier,16,260,256,26,8)
        pdf.setFont('Helvetica-Bold',10);pdf.drawString(16,227,'DELIVER TO')
        text_box(target['name'],16,211,256,28)
        address=' '.join(filter(None,[target['address'],target.get('address2',''),loc['suburb'],loc['state'],loc['postcode']]))
        text_box(address,16,178,256,48)
        text_box('FROM: '+sender['name']+', '+sender['address']+', '+origin['suburb']+' '+origin['postcode'],16,119,256,40,8)
        text_box('Actual weight: '+payload['parcels'][i-1]['actual_weight_kg']+' kg',16,69,256,16,9)
        text_box(payload.get('instructions',''),16,46,256,28,8)
        pdf.showPage()
    pdf.save()
    return output.getvalue()
