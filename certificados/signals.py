from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from .models import Inspeccion, Certificado
import os
from xhtml2pdf import pisa


@receiver(post_save, sender=Inspeccion)
def generar_certificado_borrador(sender, instance, created, **kwargs):
    """
    Al cerrar la inspección con cumple_param=True se genera el certificado
    en estado 'borrador' (PDF listo, pero pendiente de aprobación por Calidad).
    El envío al cliente y la notificación al almacén ocurren al aprobarse.
    """
    if not instance.cumple_param:
        return
    if Certificado.objects.filter(inspeccion=instance).exists():
        return

    certificado = Certificado.objects.create(
        inspeccion=instance,
        pedido=instance.lote.pedido,
        estado='borrador',
    )

    context = {
        'certificado': certificado,
        'inspeccion': instance,
        'resultados': instance.resultados.all(),
        'lote': instance.lote,
        'pedido': instance.lote.pedido,
        'cliente': instance.lote.pedido.cliente,
    }
    html_content = render_to_string('certificados/pdf_template.html', context)

    filename = f"certificado_{certificado.id}.pdf"
    relative_path = os.path.join('certificados', filename)
    absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
    os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

    with open(absolute_path, "wb") as f:
        pisa_status = pisa.CreatePDF(html_content, dest=f)

    if not pisa_status.err:
        certificado.pdf_url = relative_path
        certificado.save(update_fields=['pdf_url'])
