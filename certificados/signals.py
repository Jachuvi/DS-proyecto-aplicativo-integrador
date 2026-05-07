from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.conf import settings
from .models import Inspeccion, Certificado
import os
from xhtml2pdf import pisa


# @receiver(post_save, sender=Inspeccion)
# def generar_certificado_borrador(sender, instance, created, **kwargs):
#     """
#     Al cerrar la inspección con cumple_param=True se genera el certificado
#     en estado 'borrador' (PDF listo, pero pendiente de aprobación por Calidad).
#     El envío al cliente y la notificación al almacén ocurren al aprobarse.
#     """
#     if not instance.cumple_param:
#         return
#     if Certificado.objects.filter(inspeccion=instance).exists():
#         return
#
#     certificado = Certificado.objects.create(
#         inspeccion=instance,
#         pedido=instance.lote.pedido,
#         estado='borrador',
#     )
#
#     # Decoramos cada resultado con el rango efectivo (override de cliente o global)
#     cliente = instance.lote.pedido.cliente
#     overrides = {
#         pc.parametro_id: (pc.ref_min, pc.ref_max)
#         for pc in cliente.parametros_cliente.filter(activo=True)
#     }
#     resultados_ext = []
#     for res in instance.resultados.select_related('parametro'):
#         rmin, rmax = overrides.get(
#             res.parametro_id, (res.parametro.ref_min, res.parametro.ref_max)
#         )
#         resultados_ext.append({
#             'parametro': res.parametro,
#             'valor': res.valor_obtenido,
#             'ref_min': rmin,
#             'ref_max': rmax,
#             'desvio': res.desvio_vs_ref,
#             'fuente': 'Cliente' if res.parametro_id in overrides else 'Internacional',
#             'cumple': rmin <= res.valor_obtenido <= rmax,
#         })
#
#     context = {
#         'certificado': certificado,
#         'inspeccion': instance,
#         'resultados': resultados_ext,
#         'lote': instance.lote,
#         'pedido': instance.lote.pedido,
#         'cliente': cliente,
#     }
#     html_content = render_to_string('certificados/pdf_template.html', context)
#
#     filename = f"certificado_{certificado.id}.pdf"
#     relative_path = os.path.join('certificados', filename)
#     absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
#     os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
#
#     with open(absolute_path, "wb") as f:
#         pisa_status = pisa.CreatePDF(html_content, dest=f)
#
#     if not pisa_status.err:
#         certificado.pdf_url = relative_path
#         certificado.save(update_fields=['pdf_url'])
