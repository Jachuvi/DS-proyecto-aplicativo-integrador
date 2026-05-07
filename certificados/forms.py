from django import forms
from .models import Cliente, Producto, Venta


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "id_cliente",
            "nombre",
            "rfc",
            "direccion_fiscal_calle",
            "direccion_fiscal_numero",
            "direccion_fiscal_interior",
            "direccion_fiscal_colonia",
            "direccion_fiscal_codigo_postal",
            "direccion_fiscal_ciudad",
            "direccion_fiscal_estado",
            "direccion_entrega_misma",
            "direccion_entrega_calle",
            "direccion_entrega_numero",
            "direccion_entrega_interior",
            "direccion_entrega_colonia",
            "direccion_entrega_codigo_postal",
            "direccion_entrega_ciudad",
            "direccion_entrega_estado",
            "contacto",
            "correo_contacto",
            "requiere_certificado",
        ]
        labels = {
            "id_cliente": "Id cliente (SAP ByD)",
        }
        widgets = {
            "id_cliente": forms.TextInput(attrs={"class": "form-control", "placeholder": "ID de SAP Business ByDesign"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "rfc": forms.TextInput(attrs={"class": "form-control", "maxlength": "13"}),
            "direccion_fiscal_calle": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Calle"}
            ),
            "direccion_fiscal_numero": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Número"}
            ),
            "direccion_fiscal_interior": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Interior (opcional)"}
            ),
            "direccion_fiscal_colonia": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Colonia"}
            ),
            "direccion_fiscal_codigo_postal": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CP", "maxlength": "5"}
            ),
            "direccion_fiscal_ciudad": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ciudad"}
            ),
            "direccion_fiscal_estado": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Estado"}
            ),
            "direccion_entrega_misma": forms.CheckboxInput(
                attrs={"class": "form-check-input", "onchange": "toggleEntrega()"}
            ),
            "direccion_entrega_calle": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Calle"}
            ),
            "direccion_entrega_numero": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Número"}
            ),
            "direccion_entrega_interior": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Interior (opcional)"}
            ),
            "direccion_entrega_colonia": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Colonia"}
            ),
            "direccion_entrega_codigo_postal": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "CP", "maxlength": "5"}
            ),
            "direccion_entrega_ciudad": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Ciudad"}
            ),
            "direccion_entrega_estado": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Estado"}
            ),
            "contacto": forms.TextInput(attrs={"class": "form-control"}),
            "correo_contacto": forms.EmailInput(attrs={"class": "form-control"}),
            "requiere_certificado": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
        }

    def clean_rfc(self):
        rfc = self.cleaned_data.get("rfc")
        if rfc and len(rfc) != 13:
            raise forms.ValidationError("RFC must be exactly 13 characters.")
        return rfc

    def clean_correo_contacto(self):
        correo = self.cleaned_data.get("correo_contacto")
        if correo and not correo.endswith((".com", ".mx", ".org")):
            raise forms.ValidationError("Invalid email domain.")
        return correo


class VentaForm(forms.ModelForm):
    class Meta:
        model = Venta
        fields = ["cliente", "producto", "cantidad"]
        widgets = {
            "cliente": forms.Select(attrs={"class": "form-select select2", "data-placeholder": "Seleccione un cliente..."}),
            "producto": forms.Select(attrs={"class": "form-select select2", "data-placeholder": "Seleccione un producto..."}),
            "cantidad": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "Cantidad en kg"}),
        }
