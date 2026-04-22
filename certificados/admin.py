from django.contrib import admin
from .models import Usuario, Cliente, Equipo, Parametro, Pedido, Lote, Inspeccion, Resultado, Certificado

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'correo', 'rol')

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'rfc', 'activo')

@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ('clave', 'tipo', 'serie')

@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'unidad', 'ref_min', 'ref_max')

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'producto', 'estado')

@admin.register(Lote)
class LoteAdmin(admin.ModelAdmin):
    list_display = ('codigo_lote', 'secuencia', 'pedido')

@admin.register(Inspeccion)
class InspeccionAdmin(admin.ModelAdmin):
    list_display = ('id', 'lote', 'equipo', 'cumple_param')

@admin.register(Resultado)
class ResultadoAdmin(admin.ModelAdmin):
    list_display = ('inspeccion', 'parametro', 'valor_obtenido', 'desvio_vs_ref')

@admin.register(Certificado)
class CertificadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'inspeccion', 'fecha_emision', 'enviado')
