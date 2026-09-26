# OBSERVAPAZ

Proyecto para la Red de Observatorios para la Paz Territorial: registro
de hechos victimizantes ocurridos en los municipios de cada observatorio,
con moderación, tableros público/privado, y captura online y offline
(ODK). Núcleo Django/DRF, base de datos única PostgreSQL.

## Qué incluye

- **core/**: modelos (`Observatorio`, `PerfilUsuario`, `TipoHecho`,
  `CasoVictimizante`, `EnvioODK`), admin de Django y API REST (DRF).
- **panel/**: tres niveles de acceso:
  - `/` — tablero público consolidado (sin login, cifras agregadas de
    casos: por tipo de hecho, por observatorio, evolución mensual,
    población afectada acumulada). Nunca muestra el detalle de un caso.
  - `/tablero/` — tablero privado (requiere login), con la lista
    completa de casos. Si el usuario está ligado a un observatorio, ve
    solo su información; si es de coordinación, ve el filtro completo
    entre los 24.
  - `/caso/<id>/` — detalle completo de un caso (requiere login, y
    respeta el mismo aislamiento por observatorio).
  - `/novedades/` — bandeja de casos pendientes de revisión.
  - `/formularios/` y `/formulario/<codigo>/` — reporte de un caso,
    público, sin login.
- **docker-compose.yml**: levanta PostgreSQL, la app Django y Metabase
  (para tableros analíticos adicionales sobre la misma base de datos).

Los 24 espacios funcionales (OBS-001 a OBS-024) son registros del modelo
`Observatorio` en una única base de datos, no esquemas separados. El
aislamiento entre observatorios se maneja por cuenta de usuario
(`PerfilUsuario`), no por base de datos.

## El modelo de datos: `CasoVictimizante`

Registra un hecho victimizante: qué pasó, cuándo, dónde, presunto
responsable, cifras agregadas de población afectada (nunca nombres),
fuente y nivel de verificación, descripción, afectaciones, y
seguimiento (remisión a entidades, estado del caso). El catálogo de
tipos de hecho (`TipoHecho`) es editable desde el admin -no está fijo
en código-.

Por diseño, nunca se registran nombres de víctimas ni datos que
permitan identificarlas -solo cifras agregadas-, y cada caso nace con
`requiere_reserva` en verdadero por defecto.

## Cómo correrlo

```bash
cp .env.example .env
docker compose up --build
```

Luego, en otra terminal:

```bash
docker compose exec web python manage.py makemigrations
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

- Tablero público: http://localhost:8010/
- Tablero privado: http://localhost:8010/tablero/
- Admin de Django: http://localhost:8010/admin/
- API REST: http://localhost:8010/api/
- Metabase: http://localhost:3000/ (conéctalo a la misma base `observapaz`)

## Crear una cuenta para un observatorio

Desde `/admin/` → "Usuarios" → crea el usuario, y en la misma pantalla
asigna su "Observatorio" en la sección de perfil. Si lo dejas vacío, la
cuenta es de coordinación y ve el tablero completo.

## Cargar datos de ejemplo

```bash
docker compose exec web python manage.py cargar_ejemplo
```

Crea los 24 observatorios, el catálogo de tipos de hecho, y varios
casos de ejemplo ya aprobados (para que los tableros no se vean vacíos).

## Subdominio por observatorio (opcional)

El proyecto puede reconocer el observatorio a partir del subdominio
(ej. `obs-007.observapaz.org` muestra directo el formulario y el
tablero público de OBS-007), gracias a `core/middleware.py`. Se activa
con dos variables en el `.env`:

```ini
DOMINIO_BASE=observapaz.org
DJANGO_ALLOWED_HOSTS=observapaz.org,.observapaz.org
```

El subdominio **solo decide qué se muestra por defecto en la parte
pública** (formulario, tablero público). Nunca se usa para decidir qué
datos privados puede ver alguien -eso sigue dependiendo únicamente del
`PerfilUsuario` de la cuenta logueada-, porque el encabezado `Host` lo
puede mandar cualquiera. Ver el manual de instalación para el DNS
comodín, el certificado HTTPS wildcard, y cómo probarlo en tu propia
PC sin tener el dominio real todavía.

## Captura offline con ODK Central / ODK Collect

Para el trabajo de campo sin señal, el proyecto se conecta con **ODK
Central** (servidor aparte, ver el manual de instalación, sección 11):

- `python manage.py generar_xlsform OBS-XXX` — genera el formulario
  de reporte de casos (XLSForm) de un observatorio, con el catálogo de
  tipos de hecho activo, listo para subir a Central.
- `python manage.py sincronizar_odk` — trae los envíos nuevos desde
  Central y los convierte en `CasoVictimizante` **pendiente de
  revisión** — entra a la misma bandeja de "Novedades" que usa el
  formulario web, sin importar si el dato vino del navegador o de
  ODK Collect sin conexión. Se programa por `cron` (ver manual).

## Moderación: casos pendientes de aprobación

Los casos que llegan por el **formulario público** (sin login) o por
**ODK Collect** nacen en estado `pendiente` y **no cuentan** en los
tableros ni en las cifras oficiales hasta que alguien los apruebe. Los
casos que ingresa directamente un usuario ya logueado se aprueban solos.

- El gestor de cada observatorio ve un aviso en su tablero privado
  (`/tablero/`) y una bandeja dedicada (`/novedades/`), con botones
  para aprobar o rechazar.
- Apenas llega un caso pendiente, se envía un correo de alerta a todos
  los usuarios ligados a ese observatorio (ver la sección de correo en
  `.env.example`). Mientras no configures un SMTP real, esos correos
  solo se imprimen en los logs del contenedor
  (`docker compose logs -f web`) — útil para probar sin enviar nada de
  verdad todavía.
- Los usuarios de coordinación ven los pendientes de toda la Red.

## Cómo se conectan las páginas con la API

Las plantillas del formulario y de los tableros no reciben los datos
pre-armados desde la vista de Django: Django solo sirve la página (y
decide si tienes permiso para verla) y el JavaScript de cada plantilla
trae y guarda los datos hablando directo con `/api/`:

- El formulario público guarda con `POST /api/casos/` (abierto, sin login).
- Los tableros leen cifras agregadas con `GET /api/casos/resumen/`
  -nunca la descripción/fuente de cada caso, eso solo se ve autenticado-.
- El detalle de un caso se trae con `GET /api/casos/<id>/` -Django ya
  validó el acceso antes de servir la página; la API vuelve a
  validarlo de forma independiente-.

El aislamiento por observatorio (`PerfilUsuario`) se aplica dentro de
cada `ViewSet` (`core/views_api.py`, `core/permissions.py`), no en las
vistas de Django -así que aunque algo llame a la API directamente
(ODK Central, un script, Postman), el mismo control aplica siempre-.

## Sin multi-tenant: qué cambió

- No hay esquemas por observatorio ni base de datos separada.
- El aislamiento entre observatorios se maneja por filtro (`ForeignKey`
  a `Observatorio` a través de `PerfilUsuario`), no por base de datos ni
  esquema separado.
- Es más simple de desplegar y mantener; a cambio, todos los observatorios
  comparten las mismas tablas (con sus datos diferenciados por el campo
  `observatorio`).
