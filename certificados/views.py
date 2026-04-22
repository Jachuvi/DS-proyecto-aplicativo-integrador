from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.forms import inlineformset_factory, modelform_factory
from .models import (
    Pedido,
    Cliente,
    Lote,
    Inspeccion,
    Resultado,
    Certificado,
    Parametro,
    Equipo,
)
from django.db import transaction
import django_filters


# Access Control Mixin
class RoleRequiredMixin(UserPassesTestMixin):
    allowed_roles = []

    def test_func(self):
        return self.request.user.is_authenticated and (
            self.request.user.rol in self.allowed_roles
            or self.request.user.rol == "admin"
        )


# 1. RegistroDePedidoView
class RegistroDePedidoView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    model = Pedido
    fields = ["cliente", "producto", "cantidad"]
    template_name = "certificados/pedido_form.html"
    success_url = reverse_lazy("recepcion_pedidos")
    allowed_roles = ["ventas"]

    def form_valid(self, form):
        form.instance.estado = "pendiente"
        return super().form_valid(form)


# 2. RecepcionPedidoView (List of pending orders)
class RecepcionPedidoView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Pedido
    template_name = "certificados/recepcion_pedidos.html"
    context_object_name = "pedidos"
    allowed_roles = ["lab"]

    def get_queryset(self):
        return Pedido.objects.filter(estado="pendiente")


# 3. AsignarEquipoView (Creates Lote and Inspeccion)
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

            # Mutar el estado a "en proceso"
            pedido.estado = "aceptado"  # Assuming 'aceptado' means 'in process' or just moving forward
            # Actually, the requirement says: "Mutar el estado a 'en proceso' al asignar una instancia de Equipo"
            # But the ENUM doesn't have 'en proceso'. It has 'aceptado'.
            # I will use 'aceptado' as the 'en proceso' state for now or stick to the ENUM.
            pedido.save()

            # Create Inspeccion
            equipo_id = self.request.POST.get("equipo")
            equipo = get_object_or_404(Equipo, id=equipo_id)
            inspeccion = Inspeccion.objects.create(lote=self.object, equipo=equipo)

        return redirect("registro_resultados", pk=inspeccion.pk)


# 3. RegistroResultadosView
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

                # Validación lógica booleana
                cumple = True
                if not self.object.resultados.exists():
                    cumple = False
                else:
                    for res in self.object.resultados.all():
                        if not (
                            res.parametro.ref_min
                            <= res.valor_obtenido
                            <= res.parametro.ref_max
                        ):
                            cumple = False
                            break

                self.object.cumple_param = cumple
                self.object.save()

                # Update Pedido status final
                pedido = self.object.lote.pedido
                if cumple:
                    pedido.estado = "despachado"
                else:
                    pedido.estado = "rechazado"
                pedido.save()

        return redirect(self.success_url)


# 4. ConsultaCertificadosView
class CertificadoFilter(django_filters.FilterSet):
    fecha_emision = django_filters.DateFromToRangeFilter(field_name="fecha_emision")

    class Meta:
        model = Certificado
        fields = ["fecha_emision"]


class ConsultaCertificadosView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    model = Certificado
    template_name = "certificados/consulta_certificados.html"
    context_object_name = "certificados"
    allowed_roles = ["admin", "calidad"]

    def get_queryset(self):
        queryset = super().get_queryset()
        self.filterset = CertificadoFilter(self.request.GET, queryset=queryset)
        return self.filterset.qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filterset"] = self.filterset
        return context
