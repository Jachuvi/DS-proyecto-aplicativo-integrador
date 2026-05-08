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

# Create initial data (users, parameters, sample data, certificado)
python setup_data.py
```

## Setup
1. `pip install -r requirements.txt` (or use uv)
2. `python manage.py migrate`
3. `python setup_data.py`

## Test Users (from setup_data.py)
- **Admin**: admin@test.com / adminpassword123 (full access)
- **Ventas**: ventas@test.com / password123 (register venta)
- **Lab**: lab@test.com / password123 (inspections)
- **Control Calidad**: controlcalidad@test.com / password123 (certificates + inspections)
- **Aseguramiento Calidad**: calidad@test.com / password123 (certificates + statistics)
- **Gerente Planta**: gerenteplanta@test.com / password123 (statistics)
- **Director Operaciones**: directoroperaciones@test.com / password123 (statistics)
- **Almacén**: almacen@test.com / password123 (lotes + despachos)

## Roles & Access

| Role | Access |
|------|--------|
| **ventas** | RegistroVenta only |
| **lab** | Inspecciones Pendientes, resultados |
| **control calidad** | Inspecciones + Certificados |
| **aseguramiento calidad** | Certificados + Estadísticas |
| **operaciones** | Lotes + Pedidos/Despachos |
| **gerente planta** | Estadísticas only |
| **director operaciones** | Estadísticas only |
| **admin** | Universal access |

## Architecture
- Custom `Usuario` model (extends AbstractBaseUser) replaces Django's User
- AUTH_USER_MODEL = 'certificados.Usuario' in settings
- Uses SQLite (db.sqlite3) for development

## Key Dependencies
- django-filter (filtering)
- xhtml2pdf (PDF certificate generation)
- Select2 (searchable selects)
- resend (email sending)

## URL Structure
- Root `/` → HomeView (role-specific dashboard)
- `/ventas/registro/` → Ventas - Register new Venta
- `/laboratorio/inspecciones/` → Lab - Inspecciones pendientes
- `/laboratorio/lote/<id>/iniciar/` → Lab - Start inspection
- `/calidad/certificados/` → Certificados list
- `/calidad/certificados/nuevo/` → Create certificado
- `/calidad/certificados/<id>/ver/` → View certificado
- `/calidad/certificados/<id>/descargar/` → Download PDF
- `/almacen/lotes/` → Lotes list
- `/admin-catalogo/clientes/` → Client management (with detail view)
- `/admin-catalogo/equipos/` → Equipment management (with detail view + filters)
- `/admin/` → Django admin
- `/accounts/` → Django auth

## Sidebar Navigation (role-based)
- **Ventas**: Registrar Venta
- **Laboratorio**: Inspecciones Pendientes (lab + control calidad)
- **Calidad**: Certificados (control calidad + aseguramiento calidad)
- **Estadísticas**: (aseguramiento calidad + gerente planta + director operaciones)
- **Almacén**: Lotes, Pedidos (operaciones)
- **Administración**: Clientes, Productos, Equipos, Parámetros (admin only)

## Model Overview

### Venta
- Auto-generated orden (V-YYYYMMDD-XXXX format)
- Automatically creates a linked Pedido on save
- Estados: pendiente, aceptado, rechazado, despachado

### Cliente
- `id_cliente` field for SAP Business ByD integration
- Separate fiscal and delivery addresses
- Supports custom parameter reference values via ParametroCliente

### Parametro
- Global parameters (Humedad, Cenizas, Gluten, Falling Number, etc.)
- Equipment-specific parameters:
  - Alveógrafo: P, L, P/L, W, Ie
  - Farinógrafo: Absorción de agua, Tiempo de desarrollo, Estabilidad, Grado de decaimiento

### ParametroCliente
- Custom reference values per client
- Overrides global Parametro ref_min/ref_max
- Marked as (P)articular in certificates vs (I)nternacional

### Pedido
- ForeignKey to Venta (auto-linked)
- Estados: pendiente, aceptado, rechazado, despachado

### Lote
- Auto-generated code (L-XXXXX)
- Associated to Pedido
- fecha_caducidad copied to Certificate

### Inspeccion
- Associated to Lote
- Auto-generated clave (A-XXXXX, B-XXXXX, etc.)
- Multiple Resultado entries

### Resultado
- Associated to Inspeccion and Parametro
- Auto-calculated desvio_vs_ref

### Certificado
- Associated to Inspeccion and Pedido
- Auto-generated folio (CERT-XXXXX)
- Estados: borrador, aprobado, despachado, rechazado, superado
- PDF generation with xhtml2pdf
- Auto-sends email via Resend on creation/approval

## Workflow

1. **Ventas** creates a Venta → Auto-creates Pedido
2. **Almacén (operaciones)** assigns Lote to Pedido
3. **Laboratorio** performs inspection on Lote → Creates Inspeccion with Resultados
4. **Control Calidad** creates Certificado from Inspeccion + Pedido
5. **Aseguramiento Calidad** approves Certificate → Auto-sends PDF to client email
6. **Almacén** completes dispatch

## Environment Variables (.env)
```
RESEND_API_KEY=re_xxxxxxxxxxxxx
RESEND_FROM_EMAIL=onboarding@resend.dev
```