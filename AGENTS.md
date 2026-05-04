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

## Architecture
- Custom `Usuario` model (extends AbstractBaseUser) replaces Django's User
- AUTH_USER_MODEL = 'certificados.Usuario' in settings
- Roles: lab, aseguramiento calidad, control calidad, planta, operaciones, admin
- Uses SQLite (db.sqlite3) for development

## Key Dependencies
- django-filter (filtering)
- xhtml2pdf (PDF certificate generation)

## URL Structure
- Root `/` → HomeView
- `/pedidos/` → Sales flow (registro, recepcion)
- `/certificados/` → Quality approval workflow
- `/despacho/` → Warehouse dispatch
- `/admin-catalogo/` → Catalog management (clients, parameters, equipment, products)
- `/trazabilidad/` → Lot traceability
- `/admin/` → Django admin
- `/accounts/` → Django auth (login/logout)