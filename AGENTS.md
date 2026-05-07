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


## TODOS

1. Changes despacho pendientes page for pedidos dont forget to update the sidebar
  - pedidos show a list of registered pedidos with filters on their status 
  - Each pedidos has an automatically generated alpha numeric id 
2. Add a another page under almacen section called lotes where there is a list in display with an option to create a lote the lote id starts with L- and some alpha numeric code is automatically generated
  - Lote registration need the user to select a product, quantity , date of the lote (automatically filled) and another date input for its expiration date 
3. In the pedidos list add and option to assign a lote 
4. Change recepcion de pedidos page in laboratorio section with an Inspecciones pendientes section there display a list of all lotes assigned to a pedido with filters for Inspected lotes, Missing inspection lotes, and All lotes. Add an action for each uninspected lote called Registro analisis inicial and Registro analisis subsecuente for already inspected lotes. Each inspection has an id with the format [A-Z]-<lote id> example for the first inpection of lote id: L-44G23 is A-44G23 and for a second inspection would be B-44G23 and so on. 
5. Under the lote inspection page show a form  with all  the registered quality paramters:
6. Add the following default seed parameter with setup_data.py: 
  – Humedad 
  – Cenizas 
  – Gluten húmedo, seco e index 
  – Falling Number 
  – Alveograma 
  – Almidón dañado 
  – Color 
  – Granulometría 
  – Microbiológicos 

In the case of broader analisis like alveograma and farinograma they are not parameters by themselves they are a set of the follwoing parameter: 

Instrumento/Método: Alveógrafo .  Parámetros Específicos:P (Tenacidad): Resistencia de la masa a la extensión, dependiente de las gluteninas.  L (Extensibilidad): Capacidad de estiramiento antes de la ruptura, dependiente de las gliadinas.  P/L: Relación de equilibrio reológico entre tenacidad y extensibilidad.  W (Fuerza panadera): Área bajo la curva, indicador del volumen potencial del pan.  Ie (Índice de elasticidad): Capacidad de recuperación elástica de la masa tras deformación.

FarinogramaInstrumento/Método: Equipo DoughLAB o Farinógrafo.  Parámetros Específicos:Absorción de agua: Porcentaje de hidratación requerido para una consistencia objetivo.  Tiempo de desarrollo de la masa: Tiempo requerido para alcanzar la consistencia máxima (Peak torque).  Estabilidad: Tolerancia mecánica durante el amasado y fermentación.  Grado de decaimiento (Softening): Caída de la consistencia por prolongación del estrés mecánico.

Each parameter associated with its corresponding lab equipment being alveografo or farinografo 


Some of the default/universal reference values are for the parameter are: 

Parameter,Reference Values,Units
Moisture (000 and 0000 flours) ,Maximum 15 ,g/100g 
"Gluten proteins (insoluble, representing glutenins and gliadins) ",80 to 85 (of total proteins) ,% 
Damaged Starch (Baking flours) ,16 to 23 ,UCD 
Falling Number (High alpha-amylase activity / low quality) ,62 ,Not specified in source 
Falling Number (Standard baking result) ,250 ,Not specified in source 
Falling Number (Low alpha-amylase activity) ,400 ,Not specified in source

Client registration has an option to set prefered parameter reference values. Make sure this ones prevail over the defailt ones in the inspectiton page.

5. Cliente registration must ask for direccion fiscal and direccion de entraga with an option to assing the dieccion de entraga to the same direccion fiscal. 
6. Remove deprecated view  panel Django (jsut sidebar) , Historial por lote, Estadisticas. Dont forget to remove them from the sidebar
7. Under the Certificados section show a list of all existing certifcados and add an option to generate one and for an existing one to edit them. The certificato its an html industiral quality certificate including the folowing field: 

El certificado de calidad deberá contener los siguientes datos: Número de lote de producción, Número de orden de compra (pedido) del cliente, Cantidad solicitada, Cantidad total por entrega, Número de factura, Fecha de envío, Fecha de caducidad, Resultado del (los) análisis realizado(s), comparación contra valores de referencia (internacionales o particulares), desviación resultante, etc.

8. There has to be an option to impriir a certificte meaning converting the html into a pdf and downlaoding it.
