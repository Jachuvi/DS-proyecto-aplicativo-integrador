# AGENTS.md

## Project Overview
Django 6.0.4 project for quality certificate management in a laboratory setting.

## Commands

```bash
# Run development server
python manage.py runserver

# Database migrations
python manage.py makemigrations
python manage.py migrate

# Create initial data (users, parameters, sample data)
python setup_data.py
```

## Setup
1. `pip install -r requirements.txt` (or use uv)
2. `python manage.py migrate`
3. `python setup_data.py`

## Test Users (from setup_data.py)
- **Admin**: admin@test.com / adminpassword123
- **Lab**: lab@test.com / password123
- **Ventas**: ventas@test.com / password123
- **Calidad**: calidad@test.com / password123
- **Almacén**: almacen@test.com / password123

## Architecture
- Custom `Usuario` model (extends AbstractBaseUser) replaces Django's User
- AUTH_USER_MODEL = 'certificados.Usuario' in settings
- Roles: lab, aseguramineto calidad, control calidad, planta, operaciones, admin, ventas
- Uses SQLite (db.sqlite3) for development

## Key Dependencies
- django-filter (filtering)
- xhtml2pdf (PDF certificate generation)

## URL Structure
- Root `/` → HomeView
- `/pedidos/registro/` → Sales - Register new pedido
- `/pedidos/pendientes/` → Almacén - List all pedidos with filters
- `/laboratorio/inspecciones/` → Lab - Inspecciones pendientes
- `/laboratorio/lote/<id>/iniciar/` → Lab - Start inspection
- `/calidad/certificados/` → Calidad - List certificados
- `/calidad/certificados/nuevo/` → Calidad - Create certificado
- `/calidad/certificados/<id>/ver/` → Calidad - View certificado
- `/calidad/certificados/<id>/imprimir/` → Calidad - Print certificado
- `/calidad/certificados/<id>/descargar/` → Calidad - Download PDF
- `/almacen/lotes/` → Almacén - List/create lotes
- `/admin-catalogo/` → Catalog management (clients, parameters, equipment, products)
- `/admin/` → Django admin
- `/accounts/` → Django auth (login/logout)

## Sidebar Navigation
- **Ventas**: Registrar Pedido
- **Laboratorio**: Inspecciones Pendientes
- **Calidad**: Certificados
- **Almacén**: Lotes, Pedidos
- **Administración**: Clientes, Productos, Equipos, Parámetros

## Model Overview

### Cliente
- Has separate `direccion_fiscal` and `direccion_entrega` fields
- `direccion_entrega_misma` flag to use fiscal address for delivery
- Supports custom parameter reference values via ParametroCliente

### Producto
- Catalogo de productos (codigo, nombre, descripcion)

### Parametro
- Global parameters (Humedad, Cenizas, Gluten, Falling Number, etc.)
- Equipment-specific parameters:
  - Alveógrafo: P, L, P/L, W, Ie
  - Farinógrafo: Absorción de agua, Tiempo de desarrollo, Estabilidad, Grado de decaimiento

### Pedido
- ForeignKey to Cliente and Producto
- Estados: pendiente, aceptado, rechazado, despachado

### Lote
- Auto-generated code (L-XXXXX)
- Secuencia (A-Z)
- Associated to Pedido (optional)
- producto, cantidad, fecha_produccion, fecha_caducidad

### Inspeccion
- Associated to Lote and Equipo
- Auto-generated clave (A-XXXXX, B-XXXXX, etc.)
- Multiple Resultado entries

### Resultado
- Associated to Inspeccion and Parametro
- Auto-calculated desvio_vs_ref

### Certificado
- Associated to Inspeccion and Pedido
- Auto-generated folio (CERT-XXXXX)
- Estados: borrador, aprobado, despachado, rechazado, superado
- PDF generation support