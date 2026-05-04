from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "rfc",
            "calle",
            "numero_exterior",
            "numero_interior",
            "colonia",
            "codigo_postal",
            "ciudad",
            "estado",
            "contacto",
            "correo_contacto",
            "requiere_certificado",
            "clave_doc_especificaciones",
        ]
        widgets = {
            "calle": forms.TextInput(
                attrs={
                    "placeholder": "Calle",
                    "class": "form-control",
                    "data-autocomplete": "street_address",
                }
            ),
            "numero_exterior": forms.TextInput(
                attrs={"placeholder": "Número exterior", "class": "form-control"}
            ),
            "numero_interior": forms.TextInput(
                attrs={
                    "placeholder": "Número interior (opcional)",
                    "class": "form-control",
                }
            ),
            "colonia": forms.TextInput(
                attrs={
                    "placeholder": "Colonia",
                    "class": "form-control",
                    "data-autocomplete": "neighborhood",
                }
            ),
            "codigo_postal": forms.TextInput(
                attrs={
                    "placeholder": "Código postal",
                    "class": "form-control",
                    "maxlength": "5",
                    "data-autocomplete": "postal_code",
                }
            ),
            "ciudad": forms.TextInput(
                attrs={
                    "placeholder": "Ciudad",
                    "class": "form-control",
                    "data-autocomplete": "administrative_area_level_2",
                }
            ),
            "estado": forms.TextInput(
                attrs={
                    "placeholder": "Estado",
                    "class": "form-control",
                    "data-autocomplete": "administrative_area_level_1",
                }
            ),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "rfc": forms.TextInput(attrs={"class": "form-control", "maxlength": "13"}),
            "contacto": forms.TextInput(attrs={"class": "form-control"}),
            "correo_contacto": forms.EmailInput(attrs={"class": "form-control"}),
            "requiere_certificado": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "clave_doc_especificaciones": forms.TextInput(
                attrs={"class": "form-control"}
            ),
        }

