from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),

    # Ventas
    path('pedidos/registro/', views.RegistroDePedidoView.as_view(), name='registro_pedido'),

    # Laboratorio
    path('pedidos/recepcion/', views.RecepcionPedidoView.as_view(), name='recepcion_pedidos'),
    path('pedidos/iniciar/<int:pedido_id>/', views.IniciarInspeccionView.as_view(), name='iniciar_inspeccion'),
    path('inspeccion/registro/<int:pk>/', views.RegistroResultadosView.as_view(), name='registro_resultados'),

    # Calidad
    path('certificados/consulta/', views.ConsultaCertificadosView.as_view(), name='consulta_certificados'),
    path('certificados/<int:pk>/aprobar/', views.AprobarCertificadoView.as_view(), name='aprobar_certificado'),
    path('certificados/<int:pk>/editar/', views.EditarCertificadoView.as_view(), name='editar_certificado'),
    path('certificados/<int:pk>/leido.png', views.CertificadoLeidoView.as_view(), name='certificado_leido'),

    # Almacén
    path('despacho/pendientes/', views.PendientesDespachoView.as_view(), name='pendientes_despacho'),
    path('despacho/<int:pk>/registrar/', views.RegistrarDespachoView.as_view(), name='registrar_despacho'),

    # Administración — Clientes
    path('admin-catalogo/clientes/', views.ClienteListView.as_view(), name='cliente_list'),
    path('admin-catalogo/clientes/nuevo/', views.ClienteCreateView.as_view(), name='cliente_create'),
    path('admin-catalogo/clientes/<int:pk>/editar/', views.ClienteUpdateView.as_view(), name='cliente_update'),
    path('admin-catalogo/clientes/<int:pk>/baja/', views.ClienteBajaView.as_view(), name='cliente_baja'),

    # Administración — Parámetros por cliente
    path('admin-catalogo/clientes/<int:cliente_id>/parametros/', views.ParametroClienteListView.as_view(), name='parametro_cliente_list'),
    path('admin-catalogo/clientes/<int:cliente_id>/parametros/nuevo/', views.ParametroClienteCreateView.as_view(), name='parametro_cliente_create'),
    path('admin-catalogo/parametros-cliente/<int:pk>/editar/', views.ParametroClienteUpdateView.as_view(), name='parametro_cliente_update'),
    path('admin-catalogo/parametros-cliente/<int:pk>/eliminar/', views.ParametroClienteDeleteView.as_view(), name='parametro_cliente_delete'),

    # Administración — Equipos
    path('admin-catalogo/equipos/', views.EquipoListView.as_view(), name='equipo_list'),
    path('admin-catalogo/equipos/nuevo/', views.EquipoCreateView.as_view(), name='equipo_create'),
    path('admin-catalogo/equipos/<int:pk>/editar/', views.EquipoUpdateView.as_view(), name='equipo_update'),
    path('admin-catalogo/equipos/<int:pk>/baja/', views.EquipoBajaView.as_view(), name='equipo_baja'),

    # Administración — Parámetros (factores)
    path('admin-catalogo/parametros/', views.ParametroListView.as_view(), name='parametro_list'),
    path('admin-catalogo/parametros/nuevo/', views.ParametroCreateView.as_view(), name='parametro_create'),
    path('admin-catalogo/parametros/<int:pk>/editar/', views.ParametroUpdateView.as_view(), name='parametro_update'),
    path('admin-catalogo/parametros/<int:pk>/baja/', views.ParametroBajaView.as_view(), name='parametro_baja'),

    # Administración — Productos
    path('admin-catalogo/productos/', views.ProductoListView.as_view(), name='producto_list'),
    path('admin-catalogo/productos/nuevo/', views.ProductoCreateView.as_view(), name='producto_create'),
    path('admin-catalogo/productos/<int:pk>/editar/', views.ProductoUpdateView.as_view(), name='producto_update'),
    path('admin-catalogo/productos/<int:pk>/baja/', views.ProductoBajaView.as_view(), name='producto_baja'),

    # Estadísticas (calidad / consulta / admin)
    path('estadisticas/', views.EstadisticasView.as_view(), name='estadisticas'),

    # Trazabilidad por lote
    path('trazabilidad/', views.HistorialLoteIndexView.as_view(), name='historial_index'),
    path('trazabilidad/lote/<int:pk>/', views.HistorialLoteView.as_view(), name='historial_lote'),
]
