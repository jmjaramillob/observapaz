<<<<<<< HEAD
# OBSERVAPAZ

Proyecto base (sin multi-tenant) para la Red de Observatorios para la Paz
Territorial: núcleo Django/DRF, base de datos única PostgreSQL/PostGIS,
panel web de indicadores y punto de entrada para envíos de ODK.

## Qué incluye

- **core/**: modelos (`Observatorio`, `CategoriaIndicador`, `Indicador`,
  `RegistroIndicador`, `EnvioODK`), admin de Django y API REST (DRF).
- **panel/**: tablero consolidado (`/`) y tablero individual por indicador
  (`/indicador/<id>/`) con gráfico de serie histórica (Chart.js).
- **docker-compose.yml**: levanta PostgreSQL/PostGIS, la app Django y
  Metabase (para tableros analíticos adicionales sobre la misma base de datos).

Los 24 espacios funcionales (OBS-001 a OBS-024) ahora son simples registros
del modelo `Observatorio` en una única base de datos, no esquemas separados.

## Cómo correrlo

```bash
cp .env.example .env
docker compose up --build
```

Luego, en otra terminal:

```bash
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

- Panel de indicadores: http://localhost:8000/
- Admin de Django: http://localhost:8000/admin/
- API REST: http://localhost:8000/api/
- Metabase: http://localhost:3000/ (conéctalo a la misma base `observapaz`)

## Cargar datos de ejemplo

Desde el admin puedes crear observatorios, categorías, indicadores y
registros manualmente. Para producción, los envíos de ODK Central se
reciben en el endpoint `/api/envios-odk/` (vía `POST`) y luego se procesan
hacia `RegistroIndicador` con un comando de management o una tarea
programada (no incluida en este esqueleto, se agrega según el formulario
ODK real que definas).

## Sin multi-tenant: qué cambió

- Ya no hay `django-tenants` ni esquemas por observatorio.
- El aislamiento entre observatorios se maneja por filtro (`ForeignKey`
  a `Observatorio`), no por base de datos ni esquema separado.
- Es más simple de desplegar y mantener; a cambio, todos los observatorios
  comparten las mismas tablas (con sus datos diferenciados por el campo
  `observatorio`).
=======
# observapaz
>>>>>>> 130b46e0a85287793e5c30953c5369beb354c4c2
