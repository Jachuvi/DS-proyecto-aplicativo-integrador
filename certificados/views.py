import os
from datetime import timedelta

from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.views.generic import ListView, CreateView, UpdateView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.core.mail import EmailMessage
from django.conf import settings
from django.db import transaction
from django.forms import inlineformset_factory
from django.utils import timezone

import django_filters

from .models import (
    Pedido,
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
        ctx["certificados_por_aprobar"] = Certificado.objects.filter(estado="borrador").count()
        ctx["certificados_por_despachar"] = Certificado.objects.filter(estado="aprobado").count()
        return ctx


# ---------------------------------------------------------------------------
# Access control
# ---------------------------------------------------------------------------
class RoleRequiredMixin(UserPassesTestMixin):
    allowed_roles = []

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.rol in self.allowed_roles
            or self.request.user.rol == "admin"
        )


# ---------------------------------------------------------------------------
# Ventas — Registro de pedido
# ---------------------------------------------------------------------------
class RegistroDePedidoView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Pedido
    fields = ["cliente", "producto", "cantidad"]
    template_name = "certificados/pedido_form.html"
    success_url = reverse_lazy("recepcion_pedidos")
    allowed_roles = ["ventas"]

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
    allowed_roles = ["lab"]

    def get_queryset(self):
        return Pedido.objects.filter(estado="pendiente")


class IniciarInspeccionView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Lote
    fields = ["codigo_lote", "secuencia"]
    template_name = "certificados/iniciar_inspeccion.html"
    allowed_roles = ["lab"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["pedido"] = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        context["equipos"] = Equipo.objects.all()
        return context

    def form_valid(self, form):
        pedido = get_object_or_404(Pedido, id=self.kwargs["pedido_id"])
        with transaction.atomic():
            form.instance.pedido = pedido
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


class RegistroResultadosView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Inspeccion
    fields = []
    template_name = "certificados/registro_resultados.html"
    success_url = reverse_lazy("recepcion_pedidos")
    allowed_roles = ["lab"]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        if self.request.POST:
            data["resultados"] = ResultadoFormSet(self.request.POST, instance=self.object)
        else:
            data["resultados"] = ResultadoFormSet(instance=self.object)
        return data

    def form_valid(self, form):
        context = self.get_context_data()
        resultados = context["resultados"]
        with transaction.atomic():
            if resultados.is_valid():
                resultados.save()

                cliente_id = self.object.lote.pedido.cliente_id
                overrides = {
                    pc.parametro_id: (pc.ref_min, pc.ref_max)
                    for pc in ParametroCliente.objects.filter(cliente_id=cliente_id, activo=True)
                }

                cumple = self.object.resultados.exists()
                for res in self.object.resultados.all():
                    ref_min, ref_max = overrides.get(
                        res.parametro_id, (res.parametro.ref_min, res.parametro.ref_max)
                    )
                    if not (ref_min <= res.valor_obtenido <= ref_max):
                        cumple = False
                        break

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
    allowed_roles = ["admin", "calidad"]

    def get_queryset(self):
        queryset = super().get_queryset().select_related(
            "inspeccion__lote", "pedido__cliente", "aprobado_por"
        ).order_by("-fecha_emision")
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
    allowed_roles = ["calidad"]

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.rol in self.allowed_roles
            or self.request.user.rol == "admin"
        )

    def post(self, request, pk):
        certificado = get_object_or_404(Certificado, pk=pk)

        if certificado.estado != "borrador":
            messages.warning(request, f"El certificado #{certificado.id} ya fue procesado.")
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
            request,
            f"Certificado #{certificado.id} aprobado y enviado al cliente."
        )
        return redirect("consulta_certificados")

    def _enviar_al_cliente(self, certificado):
        if not certificado.pdf_url:
            return
        correo_cliente = certificado.pedido.cliente.correo_contacto
        absolute_path = os.path.join(settings.MEDIA_ROOT, certificado.pdf_url)
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
            with open(absolute_path, "rb") as f:
                email.attach(os.path.basename(absolute_path), f.read(), "application/pdf")
            email.send()
            certificado.enviado = True
            certificado.save(update_fields=["enviado"])
        except Exception as e:
            print(f"Error enviando correo al cliente: {e}")

    def _notificar_almacen(self, certificado):
        destinatarios = list(
            Usuario.objects.filter(rol="almacen", is_active=True)
            .values_list("correo", flat=True)
        )
        if not destinatarios:
            return
        try:
            EmailMessage(
                subject=f"Certificado aprobado - Preparar despacho pedido {certificado.pedido.id}",
                body=(
                    f"Se aprobó el certificado #{certificado.id} para el pedido "
                    f"#{certificado.pedido.id} del cliente {certificado.pedido.cliente}.\n\n"
                    f"Producto: {certificado.pedido.producto}\n"
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


# ---------------------------------------------------------------------------
# Almacén — Registro de despacho
# ---------------------------------------------------------------------------
class PendientesDespachoView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Certificado
    template_name = "certificados/pendientes_despacho.html"
    context_object_name = "certificados"
    allowed_roles = ["almacen"]

    def get_queryset(self):
        return (
            Certificado.objects.filter(estado="aprobado")
            .select_related("inspeccion__lote", "pedido__cliente")
            .order_by("fecha_aprobacion")
        )


class RegistrarDespachoView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    model = Certificado
    fields = ["numero_factura", "cantidad_total_entrega"]
    template_name = "certificados/registrar_despacho.html"
    success_url = reverse_lazy("pendientes_despacho")
    allowed_roles = ["almacen"]

    def get_queryset(self):
        return Certificado.objects.filter(estado="aprobado")

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.estado = "despachado"
            self.object.fecha_envio = timezone.now()
            self.object.save()
        messages.success(
            self.request,
            f"Despacho del certificado #{self.object.id} registrado correctamente."
        )
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


class ClienteCreateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView):
    model = Cliente
    fields = ["nombre", "rfc", "domicilio_entrega", "contacto",
              "correo_contacto", "requiere_certificado"]
    template_name = "certificados/admin/cliente_form.html"
    success_url = reverse_lazy("cliente_list")
    entidad = "Cliente"
    cancel_url_name = "cliente_list"

    def form_valid(self, form):
        messages.success(self.request, f"Cliente '{form.cleaned_data['nombre']}' creado.")
        return super().form_valid(form)


class ClienteUpdateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView):
    model = Cliente
    fields = ["nombre", "rfc", "domicilio_entrega", "contacto",
              "correo_contacto", "requiere_certificado"]
    template_name = "certificados/admin/cliente_form.html"
    success_url = reverse_lazy("cliente_list")
    entidad = "Cliente"
    cancel_url_name = "cliente_list"

    def form_valid(self, form):
        messages.success(self.request, f"Cliente '{form.cleaned_data['nombre']}' actualizado.")
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
        return ParametroCliente.objects.filter(cliente_id=self.kwargs["cliente_id"]).select_related("parametro")

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
        return reverse("parametro_cliente_list", kwargs={"cliente_id": self.object.cliente_id})


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


class EquipoCreateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView):
    model = Equipo
    fields = ["clave", "tipo", "marca", "modelo", "serie", "responsable",
              "descripcion_corta", "descripcion_larga", "proveedor", "garantia_hasta"]
    template_name = "certificados/admin/equipo_form.html"
    success_url = reverse_lazy("equipo_list")
    entidad = "Equipo"
    cancel_url_name = "equipo_list"

    def form_valid(self, form):
        messages.success(self.request, f"Equipo '{form.cleaned_data['serie']}' creado.")
        return super().form_valid(form)


class EquipoUpdateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView):
    model = Equipo
    fields = ["clave", "tipo", "marca", "modelo", "serie", "responsable",
              "descripcion_corta", "descripcion_larga", "proveedor", "garantia_hasta"]
    template_name = "certificados/admin/equipo_form.html"
    success_url = reverse_lazy("equipo_list")
    entidad = "Equipo"
    cancel_url_name = "equipo_list"

    def form_valid(self, form):
        messages.success(self.request, f"Equipo '{form.cleaned_data['serie']}' actualizado.")
        return super().form_valid(form)


class EquipoBajaView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        equipo = get_object_or_404(Equipo, pk=pk)
        equipo.activo = not equipo.activo
        equipo.save(update_fields=["activo"])
        accion = "reactivado" if equipo.activo else "dado de baja"
        messages.success(request, f"Equipo {equipo.serie} {accion}.")
        return redirect("equipo_list")


# --- Parámetros globales ---
class ParametroListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Parametro
    template_name = "certificados/admin/parametro_list.html"
    context_object_name = "parametros"
    ordering = ["-activo", "nombre"]


class ParametroCreateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView):
    model = Parametro
    fields = ["nombre", "unidad", "ref_min", "ref_max", "activo"]
    template_name = "certificados/admin/parametro_form.html"
    success_url = reverse_lazy("parametro_list")
    entidad = "Parámetro"
    cancel_url_name = "parametro_list"


class ParametroUpdateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView):
    model = Parametro
    fields = ["nombre", "unidad", "ref_min", "ref_max", "activo"]
    template_name = "certificados/admin/parametro_form.html"
    success_url = reverse_lazy("parametro_list")
    entidad = "Parámetro"
    cancel_url_name = "parametro_list"


class ParametroBajaView(LoginRequiredMixin, AdminOnlyMixin, View):
    def post(self, request, pk):
        p = get_object_or_404(Parametro, pk=pk)
        p.activo = not p.activo
        p.save(update_fields=["activo"])
        messages.success(request, f"Parámetro '{p.nombre}' {'reactivado' if p.activo else 'desactivado'}.")
        return redirect("parametro_list")


# --- Productos ---
class ProductoListView(LoginRequiredMixin, AdminOnlyMixin, ListView):
    model = Producto
    template_name = "certificados/admin/producto_list.html"
    context_object_name = "productos"
    ordering = ["-activo", "nombre"]


class ProductoCreateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, CreateView):
    model = Producto
    fields = ["codigo", "nombre", "descripcion", "activo"]
    template_name = "certificados/admin/producto_form.html"
    success_url = reverse_lazy("producto_list")
    entidad = "Producto"
    cancel_url_name = "producto_list"


class ProductoUpdateView(LoginRequiredMixin, AdminOnlyMixin, CatalogoFormMixin, UpdateView):
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
        messages.success(request, f"Producto '{p.nombre}' {'reactivado' if p.activo else 'desactivado'}.")
        return redirect("producto_list")
