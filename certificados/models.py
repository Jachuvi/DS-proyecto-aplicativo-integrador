from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    def create_user(self, correo, nombre, rol, password=None):
        if not correo:
            raise ValueError("El usuario debe tener un correo electrónico")
        user = self.model(
            correo=self.normalize_email(correo),
            nombre=nombre,
            rol=rol,
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, correo, nombre, rol="admin", password=None):
        user = self.create_user(correo, nombre, rol, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user


class Usuario(AbstractBaseUser, PermissionsMixin):
    ROLES = (
        ("lab", "Laboratorio"),
        ("aseguramineto calidad", "Aseguramiento Calidad"),
        ("control calidad", "Control calidad"),
        ("planta", "Planta"),
        ("operaciones", "Operaciones"),
        ("admin", "Administrador"),
    )
    nombre = models.CharField(max_length=120)
    correo = models.EmailField(max_length=120, unique=True)
    rol = models.CharField(max_length=30, choices=ROLES)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UsuarioManager()

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre", "rol"]

    def __str__(self):
        return f"{self.nombre} ({self.rol})"


class Cliente(models.Model):
    nombre = models.CharField(max_length=255)
    rfc = models.CharField(max_length=13, unique=True)
    
    direccion_fiscal_calle = models.CharField(max_length=150, blank=True, null=True)
    direccion_fiscal_numero = models.CharField(max_length=50, blank=True, null=True)
    direccion_fiscal_interior = models.CharField(max_length=50, blank=True, null=True)
    direccion_fiscal_colonia = models.CharField(max_length=100, blank=True, null=True)
    direccion_fiscal_codigo_postal = models.CharField(max_length=5, blank=True, null=True)
    direccion_fiscal_ciudad = models.CharField(max_length=100, blank=True, null=True)
    direccion_fiscal_estado = models.CharField(max_length=100, blank=True, null=True)
    
    direccion_entrega_calle = models.CharField(max_length=150, blank=True, null=True)
    direccion_entrega_numero = models.CharField(max_length=50, blank=True, null=True)
    direccion_entrega_interior = models.CharField(max_length=50, blank=True, null=True)
    direccion_entrega_colonia = models.CharField(max_length=100, blank=True, null=True)
    direccion_entrega_codigo_postal = models.CharField(max_length=5, blank=True, null=True)
    direccion_entrega_ciudad = models.CharField(max_length=100, blank=True, null=True)
    direccion_entrega_estado = models.CharField(max_length=100, blank=True, null=True)
    direccion_entrega_misma = models.BooleanField(default=True, help_text="Usar la misma dirección fiscal para entrega")
    
    contacto = models.CharField(max_length=100)
    correo_contacto = models.EmailField()
    requiere_certificado = models.BooleanField(default=True)
    clave_doc_especificaciones = models.CharField(
        max_length=80,
        blank=True,
        null=True,
        help_text="Clave del documento de especificaciones del cliente.",
    )
    activo = models.BooleanField(default=True)
    causa_baja = models.CharField(max_length=255, blank=True, null=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    fecha_alta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre
    
    def get_direccion_fiscal(self):
        parts = []
        if self.direccion_fiscal_calle:
            parts.append(self.direccion_fiscal_calle)
        if self.direccion_fiscal_numero:
            parts.append(self.direccion_fiscal_numero)
        if self.direccion_fiscal_colonia:
            parts.append(self.direccion_fiscal_colonia)
        if self.direccion_fiscal_codigo_postal:
            parts.append(self.direccion_fiscal_codigo_postal)
        if self.direccion_fiscal_ciudad:
            parts.append(self.direccion_fiscal_ciudad)
        if self.direccion_fiscal_estado:
            parts.append(self.direccion_fiscal_estado)
        return ", ".join(parts) if parts else ""
    
    def get_direccion_entrega(self):
        if self.direccion_entrega_misma:
            return self.get_direccion_fiscal()
        parts = []
        if self.direccion_entrega_calle:
            parts.append(self.direccion_entrega_calle)
        if self.direccion_entrega_numero:
            parts.append(self.direccion_entrega_numero)
        if self.direccion_entrega_colonia:
            parts.append(self.direccion_entrega_colonia)
        if self.direccion_entrega_codigo_postal:
            parts.append(self.direccion_entrega_codigo_postal)
        if self.direccion_entrega_ciudad:
            parts.append(self.direccion_entrega_ciudad)
        if self.direccion_entrega_estado:
            parts.append(self.direccion_entrega_estado)
        return ", ".join(parts) if parts else ""


class Producto(models.Model):
    codigo = models.CharField(max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    fecha_alta = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Equipo(models.Model):
    TIPOS = (
        ("alveografo", "Alveógrafo"),
        ("farinografo", "Farinógrafo"),
    )
    clave = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    serie = models.CharField(max_length=100, unique=True)
    responsable = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    descripcion_corta = models.CharField(max_length=255, blank=True)
    descripcion_larga = models.TextField(blank=True)
    proveedor = models.CharField(max_length=150, blank=True)
    fecha_adquisicion = models.DateField(blank=True, null=True)
    garantia_hasta = models.DateField(blank=True, null=True)
    ubicacion = models.CharField(max_length=150, blank=True)
    mantenimiento = models.TextField(
        blank=True, help_text="Plan / bitácora resumida de mantenimiento."
    )
    activo = models.BooleanField(default=True)
    causa_baja = models.CharField(max_length=255, blank=True, null=True)
    fecha_baja = models.DateTimeField(blank=True, null=True)
    fecha_alta = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.serie}"


class Parametro(models.Model):
    """
    Catálogo de parámetros (factores) de calidad. Pueden ser globales (equipo=null)
    o específicos del equipo que los analiza, en cuyo caso llevan también la
    desviación admisible y la especificación interna de la planta.
    """

    equipo = models.ForeignKey(
        Equipo,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="parametros",
        help_text="Equipo que analiza este factor. Vacío = parámetro global.",
    )
    clave_factor = models.CharField(max_length=30, blank=True)
    nombre = models.CharField(max_length=100)
    unidad = models.CharField(max_length=20)
    ref_min = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Límite inferior de referencia internacional.",
    )
    ref_max = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        help_text="Límite superior de referencia internacional.",
    )
    desviacion = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Grado de error admisible.",
    )
    especificacion_interna = models.CharField(
        max_length=200, blank=True, help_text="Especificación interna de la planta."
    )
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre


class ParametroCliente(models.Model):
    """Rangos de referencia específicos por cliente (override del global)."""

    cliente = models.ForeignKey(
        Cliente, on_delete=models.CASCADE, related_name="parametros_cliente"
    )
    parametro = models.ForeignKey(Parametro, on_delete=models.CASCADE)
    ref_min = models.DecimalField(max_digits=8, decimal_places=2)
    ref_max = models.DecimalField(max_digits=8, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("cliente", "parametro")

    def __str__(self):
        return f"{self.cliente.nombre} - {self.parametro.nombre}"


class Pedido(models.Model):
    ESTADOS = (
        ("pendiente", "Pendiente"),
        ("aceptado", "Aceptado"),
        ("rechazado", "Rechazado"),
        ("despachado", "Despachado"),
    )
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    producto = models.CharField(max_length=255)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pedido = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")

    class Meta:
        indexes = [
            models.Index(fields=["cliente", "fecha_pedido"]),
        ]

    def __str__(self):
        return f"Pedido {self.id} - {self.producto}"


class Lote(models.Model):
    pedido = models.ForeignKey(
        Pedido, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True,
        related_name="lotes"
    )
    codigo_lote = models.CharField(max_length=50, default="L-TEMP")
    secuencia = models.CharField(max_length=1, default="A")
    producto = models.ForeignKey(
        Producto, 
        on_delete=models.CASCADE,
        blank=True,
        null=True
    )
    cantidad = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        blank=True,
        null=True
    )
    fecha_produccion = models.DateField(
        auto_now_add=True,
        blank=True,
        null=True
    )
    fecha_caducidad = models.DateField(
        blank=True,
        null=True
    )
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.codigo_lote}-{self.secuencia}"
    
    def save(self, *args, **kwargs):
        if not self.codigo_lote:
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.codigo_lote = f"L-{suffix}"
        super().save(*args, **kwargs)


class Inspeccion(models.Model):
    lote = models.ForeignKey(Lote, on_delete=models.CASCADE)
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    clave = models.CharField(max_length=50, blank=True)
    fecha_inspeccion = models.DateTimeField(default=timezone.now)
    cumple_param = models.BooleanField(default=False)
    inspeccion_origen = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reanalisis",
        help_text="Inspección anterior cuando ésta es un re-análisis (caso 2.2.9).",
    )

    def save(self, *args, **kwargs):
        if not self.clave:
            import string
            count = Inspeccion.objects.filter(lote=self.lote).count()
            letra = string.ascii_uppercase[count] if count < 26 else "Z"
            lote_id_short = self.lote.codigo_lote.replace("L-", "") if self.lote.codigo_lote else str(self.lote.id)
            self.clave = f"{letra}-{lote_id_short}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Inspección {self.clave} - {self.lote}"


class Resultado(models.Model):
    inspeccion = models.ForeignKey(
        Inspeccion, related_name="resultados", on_delete=models.CASCADE
    )
    parametro = models.ForeignKey(Parametro, on_delete=models.CASCADE)
    valor_obtenido = models.DecimalField(max_digits=8, decimal_places=2)
    desvio_vs_ref = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    def save(self, *args, **kwargs):
        # Regla de derivación empírica: valor absoluto de la diferencia entre valor_obtenido y los límites
        if self.valor_obtenido > self.parametro.ref_max:
            self.desvio_vs_ref = abs(self.valor_obtenido - self.parametro.ref_max)
        elif self.valor_obtenido < self.parametro.ref_min:
            self.desvio_vs_ref = abs(self.valor_obtenido - self.parametro.ref_min)
        else:
            self.desvio_vs_ref = 0
        super().save(*args, **kwargs)


class Certificado(models.Model):
    ESTADOS = (
        ("borrador", "Borrador"),
        ("aprobado", "Aprobado por Calidad"),
        ("despachado", "Despachado al Cliente"),
        ("rechazado", "Rechazado"),
        ("superado", "Superado por re-análisis"),
    )

    inspeccion = models.ForeignKey(Inspeccion, on_delete=models.CASCADE)
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    folio = models.CharField(max_length=50, blank=True)
    fecha_emision = models.DateTimeField(auto_now_add=True)
    pdf_url = models.CharField(max_length=255, blank=True, null=True)
    enviado = models.BooleanField(default=False)

    estado = models.CharField(max_length=20, choices=ESTADOS, default="borrador")
    aprobado_por = models.ForeignKey(
        Usuario,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="certificados_aprobados",
    )
    fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    fecha_caducidad = models.DateField(null=True, blank=True)

    numero_factura = models.CharField(max_length=50, blank=True, null=True)
    cantidad_total_entrega = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    fecha_envio = models.DateTimeField(null=True, blank=True)

    leido_cliente = models.BooleanField(default=False)
    fecha_lectura = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.folio:
            import random
            import string
            suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
            self.folio = f"CERT-{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Certificado {self.folio} - {self.inspeccion.lote}"
