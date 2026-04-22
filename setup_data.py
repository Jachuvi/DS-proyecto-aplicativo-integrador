import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from certificados.models import Usuario, Cliente, Parametro, Equipo

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

# Create Sample Parametros
if not Parametro.objects.exists():
    Parametro.objects.create(nombre='Proteína', unidad='%', ref_min=10.0, ref_max=14.0)
    Parametro.objects.create(nombre='Humedad', unidad='%', ref_min=12.0, ref_max=15.0)
    print("Sample parameters created.")

# Create Sample Cliente
if not Cliente.objects.exists():
    Cliente.objects.create(
        nombre='Harinas del Valle',
        rfc='HVA1234567890',
        domicilio_entrega='Av. Principal 123',
        contacto='Juan Perez',
        correo_contacto='juan@harinasvalle.com'
    )
    print("Sample cliente created.")

# Create Sample Equipo
if not Equipo.objects.exists():
    admin = Usuario.objects.get(correo='admin@test.com')
    Equipo.objects.create(
        clave='ALV-001',
        tipo='alveografo',
        marca='Chopin',
        modelo='MA-82',
        serie='SN12345',
        responsable=admin
    )
    print("Sample equipo created.")
