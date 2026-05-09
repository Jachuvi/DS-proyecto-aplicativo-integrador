import os
import base64
import resend
from django.conf import settings
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from io import BytesIO
from certificados.models import ParametroCliente


def send_certificate_email(certificado, pdf_content=None):
    """
    Send certificate PDF to client contact email address.

    Args:
        certificado: The Certificate model instance
        pdf_content: Optional bytes for PDF attachment. If not provided, will generate from template.
    """

    # 1. Resolución escalar directa y preservación del objeto Cliente completo
    if not certificado.pedido or not certificado.pedido.cliente:
        return False, "El certificado no tiene un pedido o cliente asociado."

    cliente_obj = certificado.pedido.cliente
    destinatario = cliente_obj.correo_contacto

    if not destinatario:
        return False, "Cliente no tiene correo de contacto"

    # 2. Reemplazo de la condicional anómala y extracción de parámetros
    parametro_data = {}

    for pc in ParametroCliente.objects.filter(cliente=cliente_obj, activo=True):
        parametro_data[pc.parametro_id] = {
            "ref_min": pc.ref_min,
            "ref_max": pc.ref_max,
            "is_client": True,
        }

    for res in certificado.inspeccion.resultados.all():
        if res.parametro_id not in parametro_data:
            parametro_data[res.parametro_id] = {
                "ref_min": res.parametro.ref_min,
                "ref_max": res.parametro.ref_max,
                "is_client": False,
            }

    # Generate PDF if not provided
    if pdf_content is None:
        # 3. Concatenación de la dirección de envío para el contexto de render_to_string
        nodos_direccion = [
            certificado.direccion_envio_calle,
            certificado.direccion_envio_numero,
            certificado.direccion_envio_interior,
            certificado.direccion_envio_colonia,
            certificado.direccion_envio_codigo_postal,
            certificado.direccion_envio_ciudad,
            certificado.direccion_envio_estado,
        ]
        direccion_envio_formateada = ", ".join(filter(None, nodos_direccion))

        template = render_to_string(
            "certificados/imprimir_certificado.html",
            {
                "certificado": certificado,
                "parametro_data": parametro_data,
                "direccion_envio_str": direccion_envio_formateada,  # Inyección crítica para el PDF adjunto
                "static_root": str(settings.BASE_DIR / "static"),
            },
        )

        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(template, dest=buffer)

        if pisa_status.err:
            return False, "Error al generar PDF"

        pdf_content = buffer.getvalue()

    # Send email via Resend
    resend.api_key = settings.RESEND_API_KEY

    # 4. Uso de cliente_obj para recuperar los atributos correctamente
    params = {
        "from": settings.RESEND_FROM_EMAIL,
        "to": destinatario,
        "subject": f"Certificado de Calidad - Folio {certificado.folio}",
        "html": f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #1a2a5e;">Certificado de Calidad</h2>
            <p>Estimado/a {cliente_obj.contacto},</p>
            <p>Adjunto encontrará el certificado de análisis de calidad correspondiente al:</p>
            <ul>
                <li><strong>Lote:</strong> {certificado.inspeccion.lote.codigo_lote}-{certificado.inspeccion.lote.secuencia}</li>
                <li><strong>Producto:</strong> {certificado.inspeccion.lote.producto.nombre}</li>
                <li><strong>Cliente:</strong> {cliente_obj.nombre}</li>
                <li><strong>Folio:</strong> {certificado.folio}</li>
            </ul>
            <p>Este documento certifica que los análisis realizados cumplen con las especificaciones de calidad requeridas.</p>
            <p>Saludos cordiales,<br>
            <strong>Departamento de Control de Calidad</strong><br>
            Harinas Elizondo</p>
        </body>
        </html>
        """,
        "attachments": [
            {
                "filename": f"Certificado_{certificado.folio}.pdf",
                "content": base64.b64encode(pdf_content).decode("utf-8"),
            }
        ],
    }

    try:
        email = resend.Emails.send(params)
        return True, f"Email enviado a {destinatario}"
    except Exception as e:
        return False, f"Error al enviar email: {str(e)}"
