import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from certificados.models import Usuario, Cliente, Parametro, Equipo, Producto
from decimal import Decimal

# Create Admin
if not Usuario.objects.filter(correo='admin@test.com').exists():
    Usuario.objects.create_superuser(
        correo='admin@test.com',
        nombre='Admin User',
        rol='admin',
        password='adminpassword123'
    )
    print("Superuser created: admin@test.com / adminpassword123")

# Create Ventas User
if not Usuario.objects.filter(correo='ventas@test.com').exists():
    Usuario.objects.create_user(
        correo='ventas@test.com',
        nombre='Ventas User',
        rol='ventas',
        password='password123'
    )
    print("Ventas user created: ventas@test.com / password123")

# Create Lab User
if not Usuario.objects.filter(correo='lab@test.com').exists():
    Usuario.objects.create_user(
        correo='lab@test.com',
        nombre='Lab User',
        rol='lab',
        password='password123'
    )
    print("Lab user created: lab@test.com / password123")

# Create Quality Users
if not Usuario.objects.filter(correo='calidad@test.com').exists():
    Usuario.objects.create_user(
        correo='calidad@test.com',
        nombre='Calidad User',
        rol='aseguramineto calidad',
        password='password123'
    )
    print("Calidad user created: calidad@test.com / password123")

if not Usuario.objects.filter(correo='almacen@test.com').exists():
    Usuario.objects.create_user(
        correo='almacen@test.com',
        nombre='Almacen User',
        rol='operaciones',
        password='password123'
    )
    print("Almacen user created: almacen@test.com / password123")

# Create Equipos
admin_user = Usuario.objects.get(correo='admin@test.com')

if not Equipo.objects.filter(tipo='alveografo').exists():
    Equipo.objects.create(
        clave='ALV-001',
        tipo='alveografo',
        marca='Chopin',
        modelo='MA-82',
        serie='SN12345',
        responsable=admin_user,
        descripcion_larga='Alveógrafo para análisis de propiedades reológicas de masa'
    )
    print("Alveógrafo equipo created.")

if not Equipo.objects.filter(tipo='farinografo').exists():
    Equipo.objects.create(
        clave='FAR-001',
        tipo='farinografo',
        marca='Chopin',
        modelo='DoughLAB',
        serie='SN67890',
        responsable=admin_user,
        descripcion_larga='Farinógrafo para análisis de absorción y estabilidad de masa'
    )
    print("Farinógrafo equipo created.")

alveografo = Equipo.objects.get(tipo='alveografo')
farinografo = Equipo.objects.get(tipo='farinografo')

# Create Global Parametros (not tied to specific equipment)
if not Parametro.objects.filter(nombre='Humedad').exists():
    Parametro.objects.create(
        nombre='Humedad',
        unidad='g/100g',
        ref_min=Decimal('12.0'),
        ref_max=Decimal('15.0'),
        desviacion=Decimal('0.5'),
        especificacion_interna='Máximo 15%'
    )
    print("Parametro Humedad created.")

if not Parametro.objects.filter(nombre='Cenizas').exists():
    Parametro.objects.create(
        nombre='Cenizas',
        unidad='%',
        ref_min=Decimal('0.5'),
        ref_max=Decimal('0.75'),
        desviacion=Decimal('0.1'),
        especificacion_interna='Según tipo de harina'
    )
    print("Parametro Cenizas created.")

if not Parametro.objects.filter(nombre='Gluten húmedo').exists():
    Parametro.objects.create(
        nombre='Gluten húmedo',
        unidad='%',
        ref_min=Decimal('23.0'),
        ref_max=Decimal('35.0'),
        desviacion=Decimal('2.0'),
        especificacion_interna='Según especificación de cliente'
    )
    print("Parametro Gluten húmedo created.")

if not Parametro.objects.filter(nombre='Gluten seco').exists():
    Parametro.objects.create(
        nombre='Gluten seco',
        unidad='%',
        ref_min=Decimal('8.0'),
        ref_max=Decimal('12.0'),
        desviacion=Decimal('1.0'),
        especificacion_interna='Según especificación de cliente'
    )
    print("Parametro Gluten seco created.")

if not Parametro.objects.filter(nombre='Índice de Gluten').exists():
    Parametro.objects.create(
        nombre='Índice de Gluten',
        unidad='%',
        ref_min=Decimal('25.0'),
        ref_max=Decimal('95.0'),
        desviacion=Decimal('5.0'),
        especificacion_interna='Índice = (Gluten seco / Gluten húmedo) × 100'
    )
    print("Parametro Índice de Gluten created.")

if not Parametro.objects.filter(nombre='Falling Number').exists():
    Parametro.objects.create(
        nombre='Falling Number',
        unidad='s',
        ref_min=Decimal('250.0'),
        ref_max=Decimal('400.0'),
        desviacion=Decimal('20.0'),
        especificacion_interna='62=alta amilasa, 250=estándar, 400=baja amilasa'
    )
    print("Parametro Falling Number created.")

if not Parametro.objects.filter(nombre='Almidón dañado').exists():
    Parametro.objects.create(
        nombre='Almidón dañado',
        unidad='UCD',
        ref_min=Decimal('16.0'),
        ref_max=Decimal('23.0'),
        desviacion=Decimal('2.0'),
        especificacion_interna='Para harinas panaderas: 16-23 UCD'
    )
    print("Parametro Almidón dañado created.")

if not Parametro.objects.filter(nombre='Color').exists():
    Parametro.objects.create(
        nombre='Color',
        unidad='Minolta',
        ref_min=Decimal('85.0'),
        ref_max=Decimal('95.0'),
        desviacion=Decimal('2.0'),
        especificacion_interna='Valor L* (luminosidad) - mayor = más blanco'
    )
    print("Parametro Color created.")

if not Parametro.objects.filter(nombre='Granulometría').exists():
    Parametro.objects.create(
        nombre='Granulometría',
        unidad='%',
        ref_min=Decimal('95.0'),
        ref_max=Decimal('100.0'),
        desviacion=Decimal('1.0'),
        especificacion_interna='Pasante a través de tamiz'
    )
    print("Parametro Granulometría created.")

if not Parametro.objects.filter(nombre='Microscópicos').exists():
    Parametro.objects.create(
        nombre='Microscópicos',
        unidad='presencia/ausencia',
        ref_min=Decimal('0.0'),
        ref_max=Decimal('0.0'),
        desviacion=Decimal('0.0'),
        especificacion_interna='Ausencia de cuerpos extraños'
    )
    print("Parametro Microscópicos created.")

# Create Alveograma parameters
if not Parametro.objects.filter(nombre='P (Tenacidad)').exists():
    Parametro.objects.create(
        equipo=alveografo,
        nombre='P (Tenacidad)',
        unidad='mm',
        ref_min=Decimal('40.0'),
        ref_max=Decimal('120.0'),
        desviacion=Decimal('10.0'),
        especificacion_interna='Resistencia de la masa a la extensión'
    )
    print("Parametro P (Tenacidad) created.")

if not Parametro.objects.filter(nombre='L (Extensibilidad)').exists():
    Parametro.objects.create(
        equipo=alveografo,
        nombre='L (Extensibilidad)',
        unidad='mm',
        ref_min=Decimal('20.0'),
        ref_max=Decimal('200.0'),
        desviacion=Decimal('15.0'),
        especificacion_interna='Capacidad de estiramiento antes de ruptura'
    )
    print("Parametro L (Extensibilidad) created.")

if not Parametro.objects.filter(nombre='P/L').exists():
    Parametro.objects.create(
        equipo=alveografo,
        nombre='P/L',
        unidad='ratio',
        ref_min=Decimal('0.1'),
        ref_max=Decimal('4.0'),
        desviacion=Decimal('0.3'),
        especificacion_interna='Relación de equilibrio reológico'
    )
    print("Parametro P/L created.")

if not Parametro.objects.filter(nombre='W (Fuerza panadera)').exists():
    Parametro.objects.create(
        equipo=alveografo,
        nombre='W (Fuerza panadera)',
        unidad='10⁻⁴J',
        ref_min=Decimal('50.0'),
        ref_max=Decimal('400.0'),
        desviacion=Decimal('30.0'),
        especificacion_interna='Área bajo la curva - volumen potencial'
    )
    print("Parametro W (Fuerza panadera) created.")

if not Parametro.objects.filter(nombre='Ie (Índice de elasticidad)').exists():
    Parametro.objects.create(
        equipo=alveografo,
        nombre='Ie (Índice de elasticidad)',
        unidad='%',
        ref_min=Decimal('40.0'),
        ref_max=Decimal('90.0'),
        desviacion=Decimal('5.0'),
        especificacion_interna='Capacidad de recuperación elástica'
    )
    print("Parametro Ie (Índice de elasticidad) created.")

# Create Farinograma parameters
if not Parametro.objects.filter(nombre='Absorción de agua').exists():
    Parametro.objects.create(
        equipo=farinografo,
        nombre='Absorción de agua',
        unidad='%',
        ref_min=Decimal('50.0'),
        ref_max=Decimal('70.0'),
        desviacion=Decimal('3.0'),
        especificacion_interna='Porcentaje de hidratación requerido'
    )
    print("Parametro Absorción de agua created.")

if not Parametro.objects.filter(nombre='Tiempo de desarrollo').exists():
    Parametro.objects.create(
        equipo=farinografo,
        nombre='Tiempo de desarrollo',
        unidad='min',
        ref_min=Decimal('1.0'),
        ref_max=Decimal('20.0'),
        desviacion=Decimal('2.0'),
        especificacion_interna='Tiempo para alcanzar consistencia máxima'
    )
    print("Parametro Tiempo de desarrollo created.")

if not Parametro.objects.filter(nombre='Estabilidad').exists():
    Parametro.objects.create(
        equipo=farinografo,
        nombre='Estabilidad',
        unidad='min',
        ref_min=Decimal('5.0'),
        ref_max=Decimal('25.0'),
        desviacion=Decimal('3.0'),
        especificacion_interna='Tolerancia mecánica'
    )
    print("Parametro Estabilidad created.")

if not Parametro.objects.filter(nombre='Grado de decaimiento').exists():
    Parametro.objects.create(
        equipo=farinografo,
        nombre='Grado de decaimiento',
        unidad='FU',
        ref_min=Decimal('10.0'),
        ref_max=Decimal('100.0'),
        desviacion=Decimal('15.0'),
        especificacion_interna='Caída de consistencia por estrés'
    )
    print("Parametro Grado de decaimiento created.")

# Create Sample Productos
if not Producto.objects.exists():
    producto1 = Producto.objects.create(
        codigo='HAR-000',
        nombre='Harina de Trigo 000',
        descripcion='Harina de trigo tipo 000 para panificación'
    )
    producto2 = Producto.objects.create(
        codigo='HAR-0000',
        nombre='Harina de Trigo 0000',
        descripcion='Harina de trigo tipo 0000 para repostería'
    )
    producto3 = Producto.objects.create(
        codigo='HAR-FUERTE',
        nombre='Harina Fuerte',
        descripcion='Harina de alta proteína para panificación industrial'
    )
    print("Sample productos created.")

# Create Sample Cliente
if not Cliente.objects.exists():
    Cliente.objects.create(
        nombre='Harinas del Valle',
        rfc='HVA1234567890',
        direccion_fiscal_calle='Av. Principal',
        direccion_fiscal_numero='123',
        direccion_fiscal_colonia='Centro',
        direccion_fiscal_codigo_postal='50000',
        direccion_fiscal_ciudad='Monterrey',
        direccion_fiscal_estado='Nuevo León',
        direccion_entrega_misma=True,
        contacto='Juan Perez',
        correo_contacto='juan@harinasvalle.com',
        requiere_certificado=True
    )
    print("Sample cliente created.")
else:
    print("Cliente already exists, skipping creation.")

print("Setup completed successfully!")