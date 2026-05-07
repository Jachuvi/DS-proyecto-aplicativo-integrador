import os
import string
from datetime import timedelta

from django.conf import settings
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, View, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.forms import inlineformset_factory
from django.http import HttpResponse
from django.utils import timezone

import django_filters

from .models import (
    Pedido,
    Venta,
    Cliente,
    Lote,
    Inspeccion,
    Resultado,
    Certificado,
    Equipo,
    Parametro,
    ParametroCliente,
    Producto,
    Usuario,
)
from .forms import ClienteForm, VentaForm


# 1x1 transparent PNG used as the email open-tracking pixel
_TRACKING_PIXEL = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0"
    b"\x00\x00\x00\x03\x00\x01\x9a\xc0\x12\xa3\x00\x00\x00\x00IEND\xaeB`\x82"
)


# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = "certificados/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["pedidos_pendientes"] = Pedido.objects.filter(estado="pendiente").count()
        ctx["certificados_totales"] = Certificado.objects.count()
        ctx["certificados_enviados"] = Certificado.objects.filter(enviado=True).count()
        ctx["clientes_activos"] = Cliente.objects.filter(activo=True).count()
        ctx["certificados_por_aprobar"] = Certificado.objects.filter(
            estado="borrador"
        ).count()
        ctx["certificados_por_despachar"] = Certificado.objects.filter(
            estado="aprobado"
        ).count()
        return ctx


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
class RoleRequiredMixin(UserPassesTestMixin):
    """
    Permite los roles listados en allowed_roles.
    'admin' siempre tiene acceso.
    'consulta' tiene acceso de solo lectura: para vistas que listan / consultan
    se debe incluir explícitamente en allowed_roles cuando aplique.
    """

    allowed_roles = []

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.rol in self.allowed_roles
            or self.request.user.rol == "admin"
        )


# ---------------------------------------------------------------------------
# Ventas — Registro de pedido
# ---------------------------------------------------------------------------
class RegistroVentaView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Venta
    form_class = VentaForm
    template_name = "certificados/venta_form.html"
    success_url = reverse_lazy("home")
    allowed_roles = ["ventas", "admin"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["productos"] = Producto.objects.filter(activo=True)
        return ctx

    def form_valid(self, form):
        form.instance.estado = "pendiente"
        messages.success(self.request, "Venta registrada correctamente.")
        return super().form_valid(form)


class RegistroDePedidoView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Pedido
    fields = ["cliente", "producto", "cantidad"]
    template_name = "certificados/pedido_form.html"
    success_url = reverse_lazy("iniciar_inspeccion_pendientes")
    allowed_roles = ["ventas", "admin"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["productos"] = Producto.objects.filter(activo=True)
        return ctx

    def form_valid(self, form):
        form.instance.estado = "pendiente"
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Laboratorio — Recepción e inspección
# ---------------------------------------------------------------------------
class RecepcionPedidoView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Pedido
    template_name = "certificados/recepcion_pedidos.html"
    context_object_name = "pedidos"
    allowed_roles = ["lab", "control calidad", "admin"]

    def get_queryset(self):
        return Pedido.objects.filter(estado="pendiente")


def _next_secuencia_lote(pedido):
    """Devuelve la siguiente letra A-Z disponible para el pedido."""
    usadas = set(Lote.objects.filter(pedido=pedido).values_list("secuencia", flat=True))
    for letra in string.ascii_uppercase:
        if letra not in usadas:
            return letra
    return ""


def _suggested_codigo_lote(pedido):
    return f"LOT-{timezone.now():%Y%m%d}-P{pedido.id}"


class IniciarInspeccionView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Lote
    fields = ["codigo_lote", "secuencia"]
    template_name = "certificados/iniciar_inspeccion.html"
    allowed_roles = ["lab", "control calidad", "admin"]

    def get_initial(self):
        initial = super().get_initial()
        pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        initial["codigo_lote"] = _suggested_codigo_lote(pedido)
        initial["secuencia"] = _next_secuencia_lote(pedido)
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        context["pedido"] = pedido
        context["equipos"] = Equipo.objects.filter(activo=True)
        context["lotes_existentes"] = Lote.objects.filter(pedido=pedido).order_by(
            "secuencia"
        )
        context["secuencia_sugerida"] = _next_secuencia_lote(pedido)
        return context

    def form_valid(self, form):
        pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        secuencia = (form.cleaned_data.get("secuencia") or "").upper().strip()

        if not secuencia or secuencia not in string.ascii_uppercase:
            form.add_error("secuencia", "La secuencia debe ser una letra de A a Z.")
            return self.form_invalid(form)
        if Lote.objects.filter(pedido=pedido, secuencia=secuencia).exists():
            form.add_error(
                "secuencia",
                f"Ya existe un lote con la secuencia '{secuencia}' para este pedido.",
            )
            return self.form_invalid(form)

        with transaction.atomic():
            form.instance.pedido = pedido
            form.instance.secuencia = secuencia
            self.object = form.save()
            pedido.estado = "aceptado"
            pedido.save()

            equipo_id = self.request.POST.get("equipo")
            equipo = get_object_or_404(Equipo, id=equipo_id)
            inspeccion = Inspeccion.objects.create(lote=self.object, equipo=equipo)

        return redirect("registro_resultados", pk=inspeccion.pk)


ResultadoFormSet = inlineformset_factory(
    Inspeccion,
    Resultado,
    fields=("parametro", "valor_obtenido"),
    extra=5,
    can_delete=True,
)


def _evaluar_cumple(inspeccion):
    """Evalúa si la inspección cumple aplicando overrides por cliente."""
    cliente_id = inspeccion.lote.pedido.cliente_id
    overrides = {
        pc.parametro_id: (pc.ref_min, pc.ref_max)
        for pc in ParametroCliente.objects.filter(cliente_id=cliente_id, activo=True)
    }
    if not inspeccion.resultados.exists():
        return False
    for res in inspeccion.resultados.all():
        ref_min, ref_max = overrides.get(
            res.parametro_id, (res.parametro.ref_min, res.parametro.ref_max)
        )
        if not (ref_min <= res.valor_obtenido <= ref_max):
            return False
    return True


class RegistroResultadosView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Inspeccion
    fields = []
    template_name = "certificados/registro_resultados.html"
    success_url = reverse_lazy("iniciar_inspeccion_pendientes")
    allowed_roles = ["lab", "control calidad", "admin"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["resultados"] = ResultadoFormSet(
                self.request.POST, instance=self.object
            )
        else:
            data["resultados"] = ResultadoFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        resultados = context["resultados"]
        with transaction.atomic():
            if resultados.is_valid():
                resultados.save()
                cumple = _evaluar_cumple(self.object)
                self.object.cumple_param = cumple
                self.object.save()

                pedido = self.object.lote.pedido
                pedido.estado = "despachado" if cumple else "rechazado"
                pedido.save()

        return redirect(self.success_url)


# ---------------------------------------------------------------------------
# Calidad — Consulta y aprobación
# ---------------------------------------------------------------------------
class CertificadoFilter(django_filters.FilterSet):
    fecha_emision = django_filters.DateFromToRangeFilter(field_name="fecha_emision")
    estado = django_filters.ChoiceFilter(choices=Certificado.ESTADOS)

    class Meta:
        model = Certificado
        fields = ["fecha_emision", "estado"]


class ConsultaCertificadosView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Certificado
    template_name = "certificados/consulta_certificados.html"
    context_object_name = "certificados"
    allowed_roles = ["admin", "control calidad"]

    def get_queryset(self):
        queryset = (
            super()
            .get_queryset()
            .select_related("inspeccion__lote", "pedido__cliente", "aprobado_por")
            .order_by("-fecha_emision")
        )
        self.filterset = CertificadoFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filterset"] = self.filterset
        return context


class AprobarCertificadoView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Aprueba un certificado en borrador: marca estado='aprobado',
    calcula fecha de caducidad (6 meses), envía el PDF al cliente
    y notifica al almacén para preparar despacho.
    """

    allowed_roles = ["aseguramiento calidad", "control calidad", "admin"]

    def post(self, request, pk):
        certificado = get_object_or_404(Certificado, pk=pk)

        if certificado.estado != "borrador":
            messages.warning(
                request, f"El certificado #{certificado.id} ya fue procesado."
            )
            return redirect("consulta_certificados")

        with transaction.atomic():
            certificado.estado = "aprobado"
            certificado.aprobado_por = request.user
            certificado.fecha_aprobacion = timezone.now()
            certificado.fecha_caducidad = (timezone.now() + timedelta(days=180)).date()
            certificado.save()

        self._enviar_al_cliente(certificado)
        self._notificar_almacen(certificado)

        messages.success(
            request, f"Certificado #{certificado.id} aprobado y enviado al cliente."
        )
        return redirect("consulta_certificados")

    def _enviar_al_cliente(self, certificado):
        if not certificado.pdf_url:
            return
        correo_cliente = certificado.pedido.cliente.correo_contacto
        absolute_path = os.path.join(settings.MEDIA_ROOT, certificado.pdf_url)
        tracking_url = self.request.build_absolute_uri(
            reverse("certificado_leido", kwargs={"pk": certificado.pk})
        )
        try:
            email = EmailMessage(
                subject=f"Certificado de Calidad - Pedido {certificado.pedido.id}",
                body=(
                    f"Estimado cliente,\n\n"
                    f"Adjunto encontrará el certificado de calidad correspondiente "
                    f"a su pedido #{certificado.pedido.id}.\n\n"
                    f"Válido hasta: {certificado.fecha_caducidad}.\n"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[correo_cliente],
            )
            # Versión HTML con pixel de seguimiento (acuse de lectura)
            html_body = (
                f"<p>Estimado cliente,</p>"
                f"<p>Adjunto encontrará el certificado de calidad correspondiente "
                f"a su pedido <strong>#{certificado.pedido.id}</strong>.</p>"
                f"<p>Válido hasta: <strong>{certificado.fecha_caducidad}</strong>.</p>"
                f'<img src="{tracking_url}" width="1" height="1" alt="" '
                f'style="display:none">'
            )
            email.content_subtype = "html"
            email.body = html_body
            with open(absolute_path, "rb") as f:
                email.attach(
                    os.path.basename(absolute_path), f.read(), "application/pdf"
                )
            email.send()
            certificado.enviado = True
            certificado.save(update_fields=["enviado"])
        except Exception as e:
            print(f"Error enviando correo al cliente: {e}")

    def _notificar_almacen(self, certificado):
        destinatarios = list(
            Usuario.objects.filter(rol="almacen", is_active=True).values_list(
                "correo", flat=True
            )
        )
        if not destinatarios:
            return
        try:
            EmailMessage(
                subject=f"Certificado aprobado - Preparar despacho pedido {certificado.pedido.id}",
                body=(
                    f"Se aprobó el certificado #{certificado.id} para el pedido "
                    f"#{certificado.pedido.id} del cliente {certificado.pedido.cliente}.\n\n"
                    f"Producto: {certificado.pedido.producto.nombre}\n"
                    f"Cantidad: {certificado.pedido.cantidad}\n"
                    f"Lote: {certificado.inspeccion.lote}\n\n"
                    f"Favor de preparar el despacho y registrar el número de factura "
                    f"desde el módulo de Almacén."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=destinatarios,
            ).send()
        except Exception as e:
            print(f"Error notificando al almacén: {e}")


class CertificadoLeidoView(View):
    """Endpoint del pixel de tracking — registra la lectura del correo."""

    def get(self, request, pk):
        try:
            cert = Certificado.objects.get(pk=pk)
            if not cert.leido_cliente:
                cert.leido_cliente = True
                cert.fecha_lectura = timezone.now()
                cert.save(update_fields=["leido_cliente", "fecha_lectura"])
        except Certificado.DoesNotExist:
            pass
        return HttpResponse(_TRACKING_PIXEL, content_type="image/png")


# ---------------------------------------------------------------------------
# Calidad — Edición de certificado (caso 2.2.9)
# ---------------------------------------------------------------------------
ReanalisisFormSet = inlineformset_factory(
    Inspeccion,
    Resultado,
    fields=("parametro", "valor_obtenido"),
    extra=0,
    can_delete=False,
)


class EditarCertificadoView(LoginRequiredMixin, RoleRequiredMixin, View):
    """
    Caso 2.2.9: el usuario edita los resultados del certificado y la aplicación
    genera una NUEVA inspección (con la siguiente secuencia A-Z del lote)
    y un nuevo certificado en borrador, marcando el anterior como 'superado'.
    """

    template_name = "certificados/editar_certificado.html"
    allowed_roles = ["control calidad", "admin"]

    def _get_certificado(self, pk):
        return get_object_or_404(
            Certificado.objects.select_related("inspeccion__lote__pedido__cliente"),
            pk=pk,
        )

    def get(self, request, pk):
        from django.shortcuts import render

        certificado = self._get_certificado(pk)
        # Pre-cargamos un formset con los resultados actuales como punto de partida
        instance = Inspeccion(
            lote=certificado.inspeccion.lote, equipo=certificado.inspeccion.equipo
        )
        initial = [
            {"parametro": r.parametro_id, "valor_obtenido": r.valor_obtenido}
            for r in certificado.inspeccion.resultados.select_related("parametro")
        ]
        FormSet = inlineformset_factory(
            Inspeccion,
            Resultado,
            fields=("parametro", "valor_obtenido"),
            extra=len(initial) or 5,
            can_delete=False,
        )
        formset = FormSet(instance=instance, initial=initial)
        return render(
            request,
            self.template_name,
            {
                "certificado": certificado,
                "formset": formset,
            },
        )

    def post(self, request, pk):
        from django.shortcuts import render

        certificado = self._get_certificado(pk)
        lote = certificado.inspeccion.lote

        nueva_letra = _next_secuencia_lote(lote.pedido)
        if not nueva_letra:
            messages.error(
                request,
                "El pedido ya alcanzó las 26 secuencias (A–Z); no se puede generar un re-análisis.",
            )
            return redirect("consulta_certificados")

        # Crear nuevo Lote con la siguiente letra (mismo codigo_lote del pedido)
        with transaction.atomic():
            nuevo_lote = Lote.objects.create(
                pedido=lote.pedido,
                codigo_lote=lote.codigo_lote,
                secuencia=nueva_letra,
            )
            nueva_inspeccion = Inspeccion.objects.create(
                lote=nuevo_lote,
                equipo=certificado.inspeccion.equipo,
                inspeccion_origen=certificado.inspeccion,
            )

            FormSet = inlineformset_factory(
                Inspeccion,
                Resultado,
                fields=("parametro", "valor_obtenido"),
                extra=0,
                can_delete=False,
            )
            formset = FormSet(request.POST, instance=nueva_inspeccion)
            if not formset.is_valid():
                # roll back los registros recién creados
                transaction.set_rollback(True)
                return render(
                    request,
                    self.template_name,
                    {
                        "certificado": certificado,
                        "formset": formset,
                    },
                )
            formset.save()

            cumple = _evaluar_cumple(nueva_inspeccion)
            nueva_inspeccion.cumple_param = cumple
            nueva_inspeccion.save()

            # Marcar el certificado anterior como superado
            certificado.estado = "superado"
            certificado.save(update_fields=["estado"])

        messages.success(
            request,
            f"Re-análisis registrado como inspección {lote.codigo_lote}{nueva_letra}. "
            "Si cumple, se generará un nuevo certificado en borrador.",
        )
        return redirect("consulta_certificados")


# ---------------------------------------------------------------------------
# Almacén — Lotes
# ---------------------------------------------------------------------------
class LoteListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Lote
    template_name = "certificados/almacen_lotes.html"
    context_object_name = "lotes"
    allowed_roles = ["operaciones", "admin"]

    def get_queryset(self):
        return Lote.objects.select_related("pedido__cliente", "producto").order_by("-id")


class LoteCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Lote
    fields = ["producto", "cantidad", "fecha_caducidad"]
    template_name = "certificados/almacen_crear_lote.html"
    success_url = reverse_lazy("lote_list")
    allowed_roles = ["operaciones", "admin"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["productos"] = Producto.objects.filter(activo=True)
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        from django import forms
        form.fields['producto'].queryset = Producto.objects.filter(activo=True)
        form.fields['fecha_caducidad'].widget = forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
        form.fields['producto'].widget = forms.Select(attrs={'class': 'form-select'})
        form.fields['cantidad'].widget = forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
        return form

    def form_valid(self, form):
        import random
        import string
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        form.instance.codigo_lote = f"L-{suffix}"
        form.instance.secuencia = ""
        messages.success(self.request, f"Lote '{form.instance.codigo_lote}' creado.")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Almacén — Pedidos
# ---------------------------------------------------------------------------
class PendientesDespachoView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Pedido
    template_name = "certificados/pendientes_despacho.html"
    context_object_name = "pedidos"
    allowed_roles = ["operaciones", "admin"]

    def get_queryset(self):
        queryset = Pedido.objects.select_related("cliente", "producto").order_by("-fecha_pedido")
        filter_status = self.request.GET.get("filter", "todos")
        if filter_status == "pendientes":
            queryset = queryset.filter(estado="pendiente")
        elif filter_status == "aceptados":
            queryset = queryset.filter(estado="aceptado")
        elif filter_status == "despachados":
            queryset = queryset.filter(estado="despachado")
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.request.GET.get("filter", "todos")
        ctx["all_lotes"] = Lote.objects.filter(pedido__isnull=True, activo=True)
        return ctx


class AsignarLoteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["operaciones", "admin"]

    def post(self, request, pk):
        pedido = get_object_or_404(Pedido, pk=pk)
        lote_id = request.POST.get("lote_id")
        
        if not lote_id:
            messages.error(request, "Debe seleccionar un lote.")
            return redirect("pendientes_despacho")
        
        lote = get_object_or_404(Lote, id=lote_id)
        
        if lote.pedido and lote.pedido != pedido:
            messages.error(request, "El lote ya está asignado a otro pedido.")
            return redirect("pendientes_despacho")
        
        if lote.pedido == pedido:
            lote.pedido = None
            lote.save()
            messages.success(request, f"Lote {lote.codigo_lote} desasignado del pedido.")
        else:
            lote.pedido = pedido
            lote.save()
            messages.success(request, f"Lote {lote.codigo_lote} asignado al pedido.")
        
        return redirect("pendientes_despacho")


class RegistrarDespachoView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["operaciones", "admin"]

    def post(self, request, pk):
        lote = get_object_or_404(Lote, pk=pk)
        pedido_id = lote.pedido_id
        lote.pedido = None
        lote.save()
        messages.success(request, f"Lote {lote.codigo_lote}-{lote.secuencia} desasignado del pedido.")
        return redirect("pendientes_despacho")


class RegistrarDespachoView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    model = Pedido
    template_name = "certificados/registrar_despacho.html"
    context_object_name = "pedido"
    allowed_roles = ["operaciones", "admin"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lotes"] = self.object.lotes.all()
        return ctx
        return redirect(self.success_url)


# ---------------------------------------------------------------------------
# Administración — Catálogos (CRUD)
# ---------------------------------------------------------------------------
class AdminOnlyMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.rol == "admin"


class CatalogoFormMixin:
    """Inyecta título y URL de regreso al template de formulario."""

    entidad = ""
    cancel_url_name = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["entidad"] = self.entidad
        ctx["cancel_url"] = reverse(self.cancel_url_name)
        ctx["es_edicion"] = self.object is not None and self.object.pk is not None
        return ctx


# --- Clientes ---
class ClienteListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Cliente
    template_name = "certificados/admin/cliente_list.html"
    context_object_name = "clientes"
    ordering = ["-activo", "nombre"]


class ClienteCreateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView
):
    model = Cliente
    form_class = ClienteForm
    template_name = "certificados/admin/cliente_form.html"
    success_url = reverse_lazy("cliente_list")
    entidad = "Cliente"
    cancel_url_name = "cliente_list"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_maps_api_key"] = settings.GOOGLE_MAPS_API_KEY
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request, f"Cliente '{form.cleaned_data['nombre']}' creado."
        )
        return super().form_valid(form)


class ClienteUpdateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView
):
    model = Cliente
    form_class = ClienteForm
    template_name = "certificados/admin/cliente_form.html"
    success_url = reverse_lazy("cliente_list")
    entidad = "Cliente"
    cancel_url_name = "cliente_list"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["google_maps_api_key"] = settings.GOOGLE_MAPS_API_KEY
        return ctx

    def form_valid(self, form):
        messages.success(
            self.request, f"Cliente '{form.cleaned_data['nombre']}' actualizado."
        )
        return super().form_valid(form)


class ClienteBajaView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        cliente = get_object_or_404(Cliente, pk=pk)
        causa = request.POST.get("causa_baja", "").strip()
        if cliente.activo:
            cliente.activo = False
            cliente.causa_baja = causa or "Sin especificar"
            cliente.fecha_baja = timezone.now()
            cliente.save()
            messages.success(request, f"Cliente '{cliente.nombre}' dado de baja.")
        else:
            cliente.activo = True
            cliente.causa_baja = None
            cliente.fecha_baja = None
            cliente.save()
            messages.success(request, f"Cliente '{cliente.nombre}' reactivado.")
        return redirect("cliente_list")


# --- Parámetros por cliente ---
class ParametroClienteListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = ParametroCliente
    template_name = "certificados/admin/parametro_cliente_list.html"
    context_object_name = "parametros_cliente"

    def get_queryset(self):
        return ParametroCliente.objects.filter(
            cliente_id=self.kwargs["cliente_id"]
        ).select_related("parametro")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cliente"] = get_object_or_404(Cliente, pk=self.kwargs["cliente_id"])
        return ctx


class ParametroClienteCreateView(LoginRequiredMixin, AdminOnlyMixin, CreateView):
    model = ParametroCliente
    fields = ["parametro", "ref_min", "ref_max", "activo"]
    template_name = "certificados/admin/parametro_cliente_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.cliente = get_object_or_404(Cliente, pk=self.kwargs["cliente_id"])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cliente"] = self.cliente
        return ctx

    def form_valid(self, form):
        form.instance.cliente = self.cliente
        messages.success(self.request, "Parámetro del cliente guardado.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("parametro_cliente_list", kwargs={"cliente_id": self.cliente.id})


class ParametroClienteUpdateView(LoginRequiredMixin, AdminOnlyMixin, UpdateView):
    model = ParametroCliente
    fields = ["parametro", "ref_min", "ref_max", "activo"]
    template_name = "certificados/admin/parametro_cliente_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cliente"] = self.object.cliente
        return ctx

    def get_success_url(self):
        return reverse(
            "parametro_cliente_list", kwargs={"cliente_id": self.object.cliente_id}
        )


class ParametroClienteDeleteView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        pc = get_object_or_404(ParametroCliente, pk=pk)
        cliente_id = pc.cliente_id
        pc.delete()
        messages.success(request, "Parámetro del cliente eliminado.")
        return redirect("parametro_cliente_list", cliente_id=cliente_id)


# --- Equipos ---
class EquipoListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Equipo
    template_name = "certificados/admin/equipo_list.html"
    context_object_name = "equipos"
    ordering = ["-activo", "tipo", "serie"]


_EQUIPO_FIELDS = [
    "clave",
    "tipo",
    "marca",
    "modelo",
    "serie",
    "responsable",
    "descripcion_corta",
    "descripcion_larga",
    "proveedor",
    "fecha_adquisicion",
    "garantia_hasta",
    "ubicacion",
    "mantenimiento",
]


class EquipoCreateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView
):
    model = Equipo
    fields = _EQUIPO_FIELDS
    template_name = "certificados/admin/equipo_form.html"
    success_url = reverse_lazy("equipo_list")
    entidad = "Equipo"
    cancel_url_name = "equipo_list"

    def form_valid(self, form):
        messages.success(self.request, f"Equipo '{form.cleaned_data['serie']}' creado.")
        return super().form_valid(form)


class EquipoUpdateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView
):
    model = Equipo
    fields = _EQUIPO_FIELDS
    template_name = "certificados/admin/equipo_form.html"
    success_url = reverse_lazy("equipo_list")
    entidad = "Equipo"
    cancel_url_name = "equipo_list"

    def form_valid(self, form):
        messages.success(
            self.request, f"Equipo '{form.cleaned_data['serie']}' actualizado."
        )
        return super().form_valid(form)


class EquipoBajaView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        causa = request.POST.get("causa_baja", "").strip()
        if equipo.activo:
            equipo.activo = False
            equipo.causa_baja = causa or "Sin especificar"
            equipo.fecha_baja = timezone.now()
            equipo.save()
            messages.success(request, f"Equipo '{equipo.serie}' dado de baja.")
        else:
            equipo.activo = True
            equipo.causa_baja = None
            equipo.fecha_baja = None
            equipo.save()
            messages.success(request, f"Equipo '{equipo.serie}' reactivado.")
        return redirect("equipo_list")


# --- Parámetros (catálogo de factores) ---
class ParametroListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Parametro
    template_name = "certificados/admin/parametro_list.html"
    context_object_name = "parametros"
    ordering = ["-activo", "equipo__tipo", "nombre"]


_PARAMETRO_FIELDS = [
    "equipo",
    "clave_factor",
    "nombre",
    "unidad",
    "ref_min",
    "ref_max",
    "desviacion",
    "especificacion_interna",
    "activo",
]


class ParametroCreateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView
):
    model = Parametro
    fields = _PARAMETRO_FIELDS
    template_name = "certificados/admin/parametro_form.html"
    success_url = reverse_lazy("parametro_list")
    entidad = "Parámetro"
    cancel_url_name = "parametro_list"


class ParametroUpdateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView
):
    model = Parametro
    fields = _PARAMETRO_FIELDS
    template_name = "certificados/admin/parametro_form.html"
    success_url = reverse_lazy("parametro_list")
    entidad = "Parámetro"
    cancel_url_name = "parametro_list"


class ParametroBajaView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        p = get_object_or_404(Parametro, pk=pk)
        p.activo = not p.activo
        p.save(update_fields=["activo"])
        messages.success(
            request,
            f"Parámetro '{p.nombre}' {'reactivado' if p.activo else 'desactivado'}.",
        )
        return redirect("parametro_list")


# --- Productos ---
class ProductoListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Producto
    template_name = "certificados/admin/producto_list.html"
    context_object_name = "productos"
    ordering = ["-activo", "nombre"]


class ProductoCreateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView
):
    model = Producto
    fields = ["codigo", "nombre", "descripcion", "activo"]
    template_name = "certificados/admin/producto_form.html"
    success_url = reverse_lazy("producto_list")
    entidad = "Producto"
    cancel_url_name = "producto_list"


class ProductoUpdateView(
    LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView
):
    model = Producto
    fields = ["codigo", "nombre", "descripcion", "activo"]
    template_name = "certificados/admin/producto_form.html"
    success_url = reverse_lazy("producto_list")
    entidad = "Producto"
    cancel_url_name = "producto_list"


class ProductoBajaView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        p = get_object_or_404(Producto, pk=pk)
        p.activo = not p.activo
        p.save(update_fields=["activo"])
        messages.success(
            request,
            f"Producto '{p.nombre}' {'reactivado' if p.activo else 'desactivado'}.",
        )
        return redirect("producto_list")


# ---------------------------------------------------------------------------
# Estadísticas — Dashboard con gráficas
# ---------------------------------------------------------------------------
class EstadisticasView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    template_name = "certificados/estadisticas.html"
    allowed_roles = ["aseguramiento calidad", "gerente planta", "director operaciones", "admin"]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from certificados.models import Venta, Lote

        hoy = timezone.now()
        inicio = (hoy - timedelta(days=365)).replace(day=1)
        inicio_mes_actual = hoy.replace(day=1)

        # Ventas statistics
        total_ventas = Venta.objects.count()
        ventas_mes_actual = Venta.objects.filter(fecha_venta__gte=inicio_mes_actual).count()
        ventas_por_estado = dict(
            Venta.objects.values_list("estado")
            .annotate(total=Count("id"))
            .values_list("estado", "total")
        )
        venta_estado_labels = [label for _, label in Venta.ESTADOS]
        venta_estado_data = [ventas_por_estado.get(code, 0) for code, _ in Venta.ESTADOS]

        # Ventas por mes (últimos 12 meses)
        ventas_por_mes = (
            Venta.objects.filter(fecha_venta__gte=inicio)
            .annotate(mes=TruncMonth("fecha_venta"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )
        ventas_mes_labels = [row["mes"].strftime("%b %Y") for row in ventas_por_mes]
        ventas_mes_data = [row["total"] for row in ventas_por_mes]

        # Pedidos statistics
        total_pedidos = Pedido.objects.count()
        pedidos_mes_actual = Pedido.objects.filter(fecha_pedido__gte=inicio_mes_actual).count()
        por_estado_ped = dict(
            Pedido.objects.values_list("estado")
            .annotate(total=Count("id"))
            .values_list("estado", "total")
        )
        ped_labels = [label for _, label in Pedido.ESTADOS]
        ped_data = [por_estado_ped.get(code, 0) for code, _ in Pedido.ESTADOS]

        # Certificados statistics
        total_certificados = Certificado.objects.count()
        certificados_mes_actual = Certificado.objects.filter(fecha_emision__gte=inicio_mes_actual).count()
        por_estado_cert = dict(
            Certificado.objects.values_list("estado")
            .annotate(total=Count("id"))
            .values_list("estado", "total")
        )
        estado_labels = [label for _, label in Certificado.ESTADOS]
        estado_data = [por_estado_cert.get(code, 0) for code, _ in Certificado.ESTADOS]

        # Certificados por mes (últimos 12 meses)
        cert_por_mes = (
            Certificado.objects.filter(fecha_emision__gte=inicio)
            .annotate(mes=TruncMonth("fecha_emision"))
            .values("mes")
            .annotate(total=Count("id"))
            .order_by("mes")
        )
        meses_labels = [row["mes"].strftime("%b %Y") for row in cert_por_mes]
        meses_data = [row["total"] for row in cert_por_mes]

        # Inspecciones statistics
        total_insp = Inspeccion.objects.count()
        cumplen = Inspeccion.objects.filter(cumple_param=True).count()
        no_cumplen = total_insp - cumplen
        tasa = round(cumplen * 100 / total_insp, 1) if total_insp else 0

        # Top clientes
        top_clientes = (
            Cliente.objects.annotate(num_cert=Count("pedido__certificado"))
            .filter(num_cert__gt=0)
            .order_by("-num_cert")[:5]
        )
        clientes_labels = [c.nombre for c in top_clientes]
        clientes_data = [c.num_cert for c in top_clientes]

        # Top productos
        top_productos = (
            Pedido.objects.filter(producto__isnull=False)
            .values("producto__nombre")
            .annotate(total=Count("id"))
            .order_by("-total")[:5]
        )
        producto_labels = [row["producto__nombre"] for row in top_productos]
        producto_data = [row["total"] for row in top_productos]

        # Lotes statistics
        total_lotes = Lote.objects.count()
        lotes_sin_inspeccion = Lote.objects.filter(inspeccion__isnull=True).count()

        # Parámetros por tasa de cumplimiento
        from django.db.models import Q
        param_stats = []
        for param in Parametro.objects.filter(activo=True):
            resultados = Resultado.objects.filter(parametro=param)
            total = resultados.count()
            if total > 0:
                # Calcular cumplimiento usando las referencias del parámetro
                cumple_count = 0
                for res in resultados:
                    if res.valor_obtenido >= param.ref_min and res.valor_obtenido <= param.ref_max:
                        cumple_count += 1
                tasa_cumple = round(cumple_count * 100 / total, 1)
                param_stats.append({
                    'nombre': param.nombre,
                    'total': total,
                    'cumple': cumple_count,
                    'tasa': tasa_cumple
                })

        # Ordenar por tasa de cumplimiento (peores primero)
        param_stats.sort(key=lambda x: x['tasa'])
        param_tasa_labels = [p['nombre'][:20] + '...' if len(p['nombre']) > 20 else p['nombre'] for p in param_stats[:10]]
        param_tasa_data = [p['tasa'] for p in param_stats[:10]]

        ctx.update({
            # Ventas
            "total_ventas": total_ventas,
            "ventas_mes_actual": ventas_mes_actual,
            "venta_estado_labels": venta_estado_labels,
            "venta_estado_data": venta_estado_data,
            "ventas_mes_labels": ventas_mes_labels,
            "ventas_mes_data": ventas_mes_data,
            # Pedidos
            "total_pedidos": total_pedidos,
            "pedidos_mes_actual": pedidos_mes_actual,
            "ped_labels": ped_labels,
            "ped_data": ped_data,
            # Certificados
            "total_certificados": total_certificados,
            "certificados_mes_actual": certificados_mes_actual,
            "estado_labels": estado_labels,
            "estado_data": estado_data,
            "meses_labels": meses_labels,
            "meses_data": meses_data,
# Inspecciones
            "total_insp": total_insp,
            "cumplen": cumplen,
            "no_cumplen": no_cumplen,
            "tasa": tasa,
            # Otros
            "clientes_labels": clientes_labels,
            "clientes_data": clientes_data,
            "producto_labels": producto_labels,
            "producto_data": producto_data,
            "total_lotes": total_lotes,
            "lotes_sin_inspeccion": lotes_sin_inspeccion,
            "total_leidos": Certificado.objects.filter(leido_cliente=True).count(),
            "total_aprobados": Certificado.objects.filter(estado="aprobado").count(),
            "total_despachados": Certificado.objects.filter(estado="despachado").count(),
            "param_tasa_labels": param_tasa_labels,
            "param_tasa_data": param_tasa_data,
        })
        return ctx


# ---------------------------------------------------------------------------
# Trazabilidad — Historial por lote
# ---------------------------------------------------------------------------
class HistorialLoteView(LoginRequiredMixin, TemplateView):
    template_name = "certificados/historial_lote.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        lote = get_object_or_404(
            Lote.objects.select_related("pedido__cliente"),
            pk=self.kwargs["pk"],
        )
        inspecciones = (
            Inspeccion.objects.filter(lote=lote)
            .select_related("equipo")
            .prefetch_related("resultados__parametro")
            .order_by("fecha_inspeccion")
        )
        certificados = (
            Certificado.objects.filter(inspeccion__lote=lote)
            .select_related("aprobado_por")
            .order_by("fecha_emision")
        )

        overrides = {
            pc.parametro_id: (pc.ref_min, pc.ref_max)
            for pc in ParametroCliente.objects.filter(
                cliente_id=lote.pedido.cliente_id, activo=True
            )
        }

        bloques = []
        for insp in inspecciones:
            filas = []
            for res in insp.resultados.all():
                rmin, rmax = overrides.get(
                    res.parametro_id,
                    (res.parametro.ref_min, res.parametro.ref_max),
                )
                filas.append(
                    {
                        "parametro": res.parametro,
                        "valor": res.valor_obtenido,
                        "ref_min": rmin,
                        "ref_max": rmax,
                        "cumple": rmin <= res.valor_obtenido <= rmax,
                        "fuente": "Cliente"
                        if res.parametro_id in overrides
                        else "Global",
                        "desvio": res.desvio_vs_ref,
                    }
                )
            bloques.append({"inspeccion": insp, "filas": filas})

        ctx.update(
            {
                "lote": lote,
                "pedido": lote.pedido,
                "cliente": lote.pedido.cliente,
                "bloques": bloques,
                "certificados": certificados,
            }
        )
        return ctx


class HistorialLoteIndexView(LoginRequiredMixin, ListView):
    model = Lote
    template_name = "certificados/historial_index.html"
    context_object_name = "lotes"
    paginate_by = 25

    def get_queryset(self):
        return Lote.objects.select_related("pedido__cliente").order_by("-id")


class InspeccionesPendientesView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Lote
    template_name = "certificados/inspecciones_pendientes.html"
    context_object_name = "lotes"
    allowed_roles = ["lab", "control calidad", "admin"]

    def get_queryset(self):
        lotes = Lote.objects.select_related("pedido__cliente", "producto").filter(pedido__isnull=False).order_by("-id")
        filter_type = self.request.GET.get("filter", "pendientes")
        if filter_type == "pendientes":
            lotes = lotes.filter(inspeccion__isnull=True)
        elif filter_type == "inspeccionados":
            lotes = lotes.filter(inspeccion__isnull=False).distinct()
        return lotes

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = self.request.GET.get("filter", "pendientes")
        return ctx


class IniciarInspeccionFromLoteView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["lab", "control calidad", "admin"]

    def get(self, request, lote_id):
        lote = get_object_or_404(Lote, id=lote_id)
        parametros = Parametro.objects.filter(activo=True)

        count = Inspeccion.objects.filter(lote=lote).count()
        letra = string.ascii_uppercase[count] if count < 26 else "Z"
        lote_id_short = lote.codigo_lote.replace("L-", "") if lote.codigo_lote else str(lote.id)
        inspeccion_clave = f"{letra}-{lote_id_short}"

        parametro_overrides = {}
        if lote.pedido and lote.pedido.cliente:
            parametro_overrides = {
                pc.parametro_id: {
                    'ref_min': pc.ref_min,
                    'ref_max': pc.ref_max,
                    'is_client': True
                }
                for pc in ParametroCliente.objects.filter(
                    cliente=lote.pedido.cliente, activo=True
                )
            }
            for p in parametros:
                if p.id not in parametro_overrides:
                    parametro_overrides[p.id] = {
                        'ref_min': p.ref_min,
                        'ref_max': p.ref_max,
                        'is_client': False
                    }

        return render(request, "certificados/iniciar_inspeccion.html", {
            "lote": lote,
            "parametros": parametros,
            "parametros_global": parametros.filter(equipo__isnull=True),
            "parametros_alveograma": parametros.filter(equipo__tipo='alveografo'),
            "parametros_farinograma": parametros.filter(equipo__tipo='farinografo'),
            "inspeccion_clave": inspeccion_clave,
            "parametro_overrides": parametro_overrides,
        })

    def post(self, request, lote_id):
        lote = get_object_or_404(Lote, id=lote_id)
        
        parametros = Parametro.objects.filter(activo=True)
        
        with transaction.atomic():
            count = Inspeccion.objects.filter(lote=lote).count()
            letra = string.ascii_uppercase[count] if count < 26 else "Z"
            lote_id_short = lote.codigo_lote.replace("L-", "") if lote.codigo_lote else str(lote.id)
            clave = f"{letra}-{lote_id_short}"
            
            inspeccion = Inspeccion.objects.create(lote=lote, equipo_id=None, clave=clave)
            
            for p in parametros:
                include_key = f"include_param_{p.id}"
                valor_key = f"param_{p.id}"
                
                if request.POST.get(include_key):
                    valor = request.POST.get(valor_key)
                    if valor:
                        Resultado.objects.create(
                            inspeccion=inspeccion,
                            parametro=p,
                            valor_obtenido=valor
                        )
            
            inspeccion.cumple_param = True
            inspeccion.save()
        
        return redirect("iniciar_inspeccion_pendientes")


class CertificadosListView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Certificado
    template_name = "certificados/certificados_list.html"
    context_object_name = "certificados"
    allowed_roles = ["admin", "control calidad"]

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .select_related("inspeccion__lote", "pedido__cliente", "aprobado_por")
            .order_by("-fecha_emision")
        )


class CrearCertificadoView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "control calidad"]

    def get(self, request):
        lotes = Lote.objects.filter(pedido__isnull=False).order_by("-id")
        return render(request, "certificados/crear_certificado.html", {
            "lotes": lotes,
        })

    def post(self, request):
        lote_id = request.POST.get("lote")
        inspeccion_id = request.POST.get("inspeccion")
        numero_factura = request.POST.get("numero_factura")
        
        if not lote_id or not inspeccion_id:
            return render(request, "certificados/crear_certificado.html", {
                "lotes": Lote.objects.filter(pedido__isnull=False).order_by("-id"),
                "error": "Debe seleccionar lote e inspección.",
            })
        
        lote = get_object_or_404(Lote, id=lote_id)
        inspeccion = get_object_or_404(Inspeccion, id=inspeccion_id)
        
        certificado = Certificado.objects.create(
            inspeccion=inspeccion,
            pedido=lote.pedido,
            numero_factura=numero_factura or None,
            cantidad_total_entrega=lote.cantidad,
        )
        
        messages.success(request, f"Certificado {certificado.folio} creado.")
        return redirect("ver_certificado", pk=certificado.pk)


class VerCertificadoView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "control calidad"]

    def get(self, request, pk):
        certificado = get_object_or_404(
            Certificado.objects.select_related(
                "inspeccion__lote__pedido__cliente",
                "inspeccion__equipo",
                "pedido__producto",
                "aprobado_por"
            ),
            pk=pk
        )

        parametro_data = {}
        if certificado.inspeccion.lote.pedido and certificado.inspeccion.lote.pedido.cliente:
            cliente = certificado.inspeccion.lote.pedido.cliente
            for pc in ParametroCliente.objects.filter(cliente=cliente, activo=True):
                parametro_data[pc.parametro_id] = {
                    'ref_min': pc.ref_min,
                    'ref_max': pc.ref_max,
                    'is_client': True
                }
            for res in certificado.inspeccion.resultados.all():
                if res.parametro_id not in parametro_data:
                    parametro_data[res.parametro_id] = {
                        'ref_min': res.parametro.ref_min,
                        'ref_max': res.parametro.ref_max,
                        'is_client': False
                    }

        return render(request, "certificados/ver_certificado.html", {
            "certificado": certificado,
            "parametro_data": parametro_data,
        })


class ImprimirCertificadoView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "control calidad"]

    def get(self, request, pk):
        certificado = get_object_or_404(
            Certificado.objects.select_related(
                "inspeccion__lote__pedido__cliente",
                "inspeccion__equipo",
                "pedido__producto",
                "aprobado_por"
            ),
            pk=pk
        )

        parametro_data = {}
        if certificado.inspeccion.lote.pedido and certificado.inspeccion.lote.pedido.cliente:
            cliente = certificado.inspeccion.lote.pedido.cliente
            for pc in ParametroCliente.objects.filter(cliente=cliente, activo=True):
                parametro_data[pc.parametro_id] = {
                    'ref_min': pc.ref_min,
                    'ref_max': pc.ref_max,
                    'is_client': True
                }
            for res in certificado.inspeccion.resultados.all():
                if res.parametro_id not in parametro_data:
                    parametro_data[res.parametro_id] = {
                        'ref_min': res.parametro.ref_min,
                        'ref_max': res.parametro.ref_max,
                        'is_client': False
                    }

        return render(request, "certificados/imprimir_certificado.html", {
            "certificado": certificado,
            "parametro_data": parametro_data,
        })


class DescargarCertificadoPDFView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["admin", "control calidad"]

    def get(self, request, pk):
        from django.http import HttpResponse
        from xhtml2pdf import pisa
        from io import BytesIO
        import django.template.loader

        certificado = get_object_or_404(
            Certificado.objects.select_related(
                "inspeccion__lote__pedido__cliente",
                "inspeccion__equipo",
                "pedido__producto",
                "aprobado_por"
            ),
            pk=pk
        )

        parametro_data = {}
        if certificado.inspeccion.lote.pedido and certificado.inspeccion.lote.pedido.cliente:
            cliente = certificado.inspeccion.lote.pedido.cliente
            for pc in ParametroCliente.objects.filter(cliente=cliente, activo=True):
                parametro_data[pc.parametro_id] = {
                    'ref_min': pc.ref_min,
                    'ref_max': pc.ref_max,
                    'is_client': True
                }
            for res in certificado.inspeccion.resultados.all():
                if res.parametro_id not in parametro_data:
                    parametro_data[res.parametro_id] = {
                        'ref_min': res.parametro.ref_min,
                        'ref_max': res.parametro.ref_max,
                        'is_client': False
                    }

        from django.conf import settings
        static_root = settings.BASE_DIR / 'static'
        
        template = django.template.loader.get_template("certificados/imprimir_certificado.html")
        html = template.render({
            "certificado": certificado, 
            "pdf_mode": True, 
            "parametro_data": parametro_data,
            "static_root": str(static_root)
        })

        buffer = BytesIO()
        pisa_status = pisa.CreatePDF(html, dest=buffer)

        buffer.seek(0)
        response = HttpResponse(buffer.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="certificado_{certificado.id}.pdf"'
        return response


class ApiInspccionesView(LoginRequiredMixin, RoleRequiredMixin, View):
    allowed_roles = ["lab", "control calidad", "admin"]

    def get(self, request):
        from django.http import JsonResponse
        lote_id = request.GET.get("lote_id")
        if not lote_id:
            return JsonResponse([])
        
        inspecciones = Inspeccion.objects.filter(lote_id=lote_id).order_by("-id")
        data = [
            {"id": i.id, "clave": i.clave, "fecha": i.fecha_inspeccion.strftime("%d/%m/%Y")}
            for i in inspecciones
        ]
        return JsonResponse(data, safe=False)
