from django.urls import path
from . import views

urlpatterns = [
    path('', views.ConsultaCertificadosView.as_view(), name='home'),
    path('pedidos/registro/', views.RegistroDePedidoView.as_view(), name='registro_pedido'),
    path('pedidos/recepcion/', views.RecepcionPedidoView.as_view(), name='recepcion_pedidos'),
    path('pedidos/iniciar/<int:pedido_id>/', views.IniciarInspeccionView.as_view(), name='iniciar_inspeccion'),
    path('inspeccion/registro/<int:pk>/', views.RegistroResultadosView.as_view(), name='registro_resultados'),
    path('certificados/consulta/', views.ConsultaCertificadosView.as_view(), name='consulta_certificados'),
]
