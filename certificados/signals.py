from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Inspeccion, Certificado, Resultado
import os
from xhtml2pdf import pisa
from io import BytesIO

@receiver(post_save, sender=Inspeccion)
def generar_certificado_automatica(sender, instance, created, **kwargs):
    # 2. Condición de activación: Evaluar if instance.cumple_param == True:
    if created and instance.cumple_param:
        # Paso 1: Insertar nuevo registro en Certificado
        certificado = Certificado.objects.create(
            inspeccion=instance,
            pedido=instance.lote.pedido
        )
        
        # Paso 2: Compilar una plantilla HTML y procesar a PDF
        context = {
            'certificado': certificado,
            'inspeccion': instance,
            'resultados': instance.resultados.all(),
            'lote': instance.lote,
            'pedido': instance.lote.pedido,
            'cliente': instance.lote.pedido.cliente
        }
        
        html_content = render_to_string('certificados/pdf_template.html', context)
        
        # Guardar el PDF en el sistema de archivos local
        filename = f"certificado_{certificado.id}.pdf"
        relative_path = os.path.join('certificados', filename)
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)
        
        with open(absolute_path, "wb") as f:
            pisa_status = pisa.CreatePDF(html_content, dest=f)
        
        if not pisa_status.err:
            certificado.pdf_url = relative_path
            certificado.save()
            
            # Paso 3: Consultar correo del cliente
            correo_cliente = instance.lote.pedido.cliente.correo_contacto
            
            # Paso 4: Instanciar EmailMessage y enviar
            try:
                email = EmailMessage(
                    subject=f"Certificado de Calidad - Pedido {instance.lote.pedido.id}",
                    body="Adjunto encontrará el certificado de calidad correspondiente a su pedido.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[correo_cliente]
                )
                with open(absolute_path, "rb") as f:
                    email.attach(filename, f.read(), 'application/pdf')
                
                email.send()
                
                # Paso 5: Actualizar Certificado.enviado = True
                certificado.enviado = True
                certificado.save()
            except Exception as e:
                print(f"Error enviando correo: {e}")
