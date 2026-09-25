# OBSERVAPAZ

Proyecto base (sin multi-tenant) para la Red de Observatorios para la Paz
Territorial: núcleo Django/DRF, base de datos única PostgreSQL/PostGIS,
panel web de indicadores y punto de entrada para envíos de ODK.

## Qué incluye

- **core/**: modelos (`Observatorio`, `CategoriaIndicador`, `Indicador`,
  `RegistroIndicador`, `EnvioODK`, `PerfilUsuario`), admin de Django y
  API REST (DRF).
- **panel/**: tres niveles de acceso:
  - `/` — tablero público consolidado (sin login, datos agregados).
  - `/tablero/` — tablero privado (requiere login). Si el usuario está
    ligado a un observatorio, ve solo su información; si es de
    coordinación, ve el filtro completo entre los 24.
  - `/indicador/<id>/` — historial de un indicador (requiere login,
    y respeta el mismo aislamiento por observatorio).
  - `/formularios/` y `/formulario/<codigo>/` — captura pública, sin login.
- **docker-compose.yml**: levanta PostgreSQL/PostGIS, la app Django y
  Metabase (para tableros analíticos adicionales sobre la misma base de datos).

Los 24 espacios funcionales (OBS-001 a OBS-024) son registros del modelo
`Observatorio` en una única base de datos, no esquemas separados. El
aislamiento entre observatorios se maneja por cuenta de usuario
(`PerfilUsuario`), no por base de datos.

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

Para producción, los envíos de ODK Central se reciben en el endpoint
`/api/envios-odk/` (vía `POST`) y luego se procesan hacia
`RegistroIndicador` con un comando de management o una tarea programada
(no incluida en este esqueleto, se agrega según el formulario ODK real
que definas).

## Moderación: registros pendientes de aprobación

Los registros que llegan por el **formulario público** (sin login) nacen
en estado `pendiente` y **no cuentan** en los tableros ni en las cifras
oficiales hasta que alguien los apruebe. Los registros que ingresa
directamente un usuario ya logueado se aprueban solos.

- El gestor de cada observatorio ve un panel de "Novedades pendientes"
  en su tablero privado (`/tablero/`), con botones para aprobar o
  rechazar.
- Apenas llega un registro pendiente, se envía un correo de alerta a
  todos los usuarios ligados a ese observatorio (ver la sección de
  correo en `.env.example`). Mientras no configures un SMTP real, esos
  correos solo se imprimen en los logs del contenedor
  (`docker compose logs -f web`) — útil para probar sin enviar nada de
  verdad todavía.
- Los usuarios de coordinación ven los pendientes de toda la Red.

## Cómo se conectan las páginas con la API

Desde este cambio, las plantillas del formulario y de los tableros ya no
reciben los datos pre-armados desde la vista de Django: Django solo sirve
la página (y decide si tienes permiso para verla) y el JavaScript de
cada plantilla trae y guarda los datos hablando directo con `/api/`:

- El formulario público guarda con `POST /api/registros/` (abierto,
  sin login).
- Los tableros leen cifras agregadas con `GET /api/registros/resumen/`
  y `GET /api/indicadores/resumen/` -nunca la fuente/observaciones de
  cada registro, eso solo se ve autenticado-.
- El detalle de un indicador trae su historial con
  `GET /api/registros/?indicador=<id>` -Django ya validó el acceso
  antes de servir la página; la API vuelve a validarlo de forma
  independiente-.

El aislamiento por observatorio (`PerfilUsuario`) se aplica dentro de
cada `ViewSet` (`core/views_api.py`, `core/permissions.py`), no en las
vistas de Django -así que aunque algo llame a la API directamente
(ODK Central, un script, Postman), el mismo control aplica siempre-.

## Sin multi-tenant: qué cambió

- Ya no hay `django-tenants` ni esquemas por observatorio.
- El aislamiento entre observatorios se maneja por filtro (`ForeignKey`
  a `Observatorio` a través de `PerfilUsuario`), no por base de datos ni
  esquema separado.
- Es más simple de desplegar y mantener; a cambio, todos los observatorios
  comparten las mismas tablas (con sus datos diferenciados por el campo
  `observatorio`).
