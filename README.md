# SpiderShare API

Backend de SpiderShare construido con FastAPI, SQLAlchemy, Alembic, MySQL, Redis y RQ. El proyecto esta organizado por modulos de negocio para mantener separadas las rutas HTTP, los casos de uso, el dominio y la infraestructura.

## Estado Actual

La API incluye:

- Autenticacion con JWT bearer.
- Gestion de usuarios, roles, passwords, perfil y avatares.
- Integracion publica con Steam para consultar juegos de perfiles publicos.
- Gestion de videos: subida, listado publico, detalle, descarga, streaming, miniaturas, favoritos y reacciones.
- Procesado asincrono de videos con Redis + RQ y worker separado.
- Estados de procesado: `pending`, `processing`, `ready`, `failed`.
- Historial de errores de procesado en `video_processing_errors`.
- Reintento de procesado para super admin.
- Idempotencia en `POST /videos` mediante `Idempotency-Key`.
- Logging con contexto de request, usuario, worker, job y video.
- Worker de videos `jaimito_worker` con logs tecnicos y mensajes marcados estilo Jaimito.
- Migraciones Alembic ejecutadas en el arranque Docker.
- Seed automatico de super admin.
- Tests unitarios y HTTP con dependencias fake.

## Stack

- Python 3.12 en Docker.
- FastAPI + Uvicorn.
- Pydantic Settings.
- SQLAlchemy + Alembic.
- MySQL 8.4.
- Redis 7 + RQ.
- FFmpeg para transcodificacion y miniaturas.
- python-jose para JWT.
- bcrypt para passwords.
- Pytest + HTTPX para tests.

## Arquitectura

```text
app/
  bootstrap/
    app_factory.py          Crea FastAPI, middleware de logging y routers.
    seed_super_admin.py     Seed inicial opcional de super admin.
  modules/
    auth/
      application/          Login, registro y password hashing.
      entrypoints/          Rutas y schemas HTTP.
      infrastructure/       JWT.
      wiring.py             Dependencias FastAPI del modulo.
    users/
      domain/               Entidad User, roles y reglas de permisos.
      entrypoints/          Rutas y schemas HTTP.
      infrastructure/       SQLAlchemy, mappers y repositorio.
      wiring.py
    steam/
      application/          Persistencia/upsert de juegos Steam.
      domain/               Entidad SteamGame y puertos.
      entrypoints/          Ruta publica de juegos.
      infrastructure/       Cliente/repositorio/modelos/mappers.
      wiring.py
    videos/
      application/          Upload, list, get, update, delete, favorite, react, process.
      domain/               Video, estados, permisos y puertos.
      entrypoints/          Rutas, schemas, validacion e idempotencia HTTP.
      infrastructure/       Modelos, mappers, repositorio y cola RQ.
      wiring.py
  shared/
    infrastructure/
      db/                   Base SQLAlchemy y sesiones.
      providers/
        steam/              Cliente Steam Web API.
        storage/            VideoStorage y VideoTranscoder.
      idempotency.py        Tabla y repositorio de idempotencia.
      logging.py            Logging con contextvars.
      jaimito_logging.py    Mensajes del worker Jaimito.
  workers/
    video_processing.py     Worker RQ de procesado de videos.
config/
  settings.py               Variables de entorno.
migrations/
  versions/                 Migraciones Alembic.
requirements/
tests/
storage/videos/
```

Cada modulo sigue esta idea:

- `domain`: entidades, enums, reglas puras y puertos.
- `application`: casos de uso.
- `entrypoints`: HTTP, schemas, validacion y traduccion de errores.
- `infrastructure`: adaptadores concretos, SQLAlchemy, mappers y servicios externos.
- `wiring.py`: dependencias de FastAPI.

## Arranque Rapido con Docker

Para desarrollo:

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Servicios en desarrollo:

- API: `http://localhost:8000`
- Docs OpenAPI: `http://localhost:8000/docs`
- MySQL: expuesto en `${MYSQL_PORT:-3306}`
- Redis: expuesto en `${REDIS_PORT:-6379}`
- Worker: sin puerto, consume jobs desde Redis.

Healthcheck:

```bash
curl http://localhost:8000/health
```

Version:

```bash
curl http://localhost:8000/version
```

## Docker y Servicios

`docker-compose.yml` define la topologia base:

- `api`: ejecuta migraciones, seed de super admin y arranca Uvicorn.
- `worker`: ejecuta `python -m app.workers.video_processing`.
- `redis`: cola RQ interna, sin puerto publicado en produccion.
- `mysql`: base de datos con volumen persistente.
- `video_storage`: volumen persistente para videos.
- `proxy_network`: red externa para proxy inverso si se usa Portainer/Caddy.

`docker-compose.dev.yml` sobreescribe desarrollo:

- Monta el codigo local en `/app`.
- Arranca Uvicorn con `--reload`.
- Publica Redis y MySQL para depuracion local.
- Monta `./storage/videos`.

Comandos utiles:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api sh
docker compose -f docker-compose.yml -f docker-compose.dev.yml down
```

Produccion/Portainer:

```bash
docker compose up --build -d
```

En produccion revisa que exista la red externa configurada con `PROXY_NETWORK_NAME` si usas el compose base tal cual.

## Variables de Entorno

El proyecto lee `.env` en local y tambien `stack.env` si existe en Docker/Portainer.

Variables principales:

| Variable | Uso |
| --- | --- |
| `APP_NAME` | Nombre de la aplicacion. |
| `APP_VERSION` | Version devuelta por `/version`. |
| `APP_ENV` | Entorno logico. `local`, `dev` o `development` activan logging DEBUG. |
| `APP_DEBUG` | Flag de debug. |
| `APP_HOST` | Host esperado para arranque local si se usa externamente. |
| `APP_PORT` | Puerto publicado por Docker para la API. |
| `DATABASE_URL` | URL SQLAlchemy usada por app y Alembic. |
| `MYSQL_HOST` | Host MySQL para compose/configuracion auxiliar. |
| `MYSQL_PORT` | Puerto MySQL publicado en desarrollo. |
| `MYSQL_DATABASE` | Base de datos MySQL. |
| `MYSQL_USER` | Usuario MySQL. |
| `MYSQL_PASSWORD` | Password MySQL. |
| `MYSQL_ROOT_PASSWORD` | Password root MySQL. |
| `SECRET_KEY` | Clave para firmar JWT. Debe ser larga y secreta. |
| `JWT_ALGORITHM` | Algoritmo JWT. Por defecto `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Minutos de vida del token. |
| `SUPER_ADMIN_USERNAME` | Username inicial del super admin. |
| `SUPER_ADMIN_PASSWORD` | Password inicial del super admin. |
| `STEAM_WEB_API_KEY` | API key de Steam. Necesaria para consultar Steam real. |
| `STEAM_WEB_API_BASE_URL` | URL base de Steam Web API. |
| `VIDEO_STORAGE_PATH` | Carpeta/volumen donde se guardan originales, variantes y miniaturas. |
| `MAX_VIDEO_SIZE_BYTES` | Tamano maximo de subida. Por defecto `524288000` bytes. |
| `MAX_VIDEO_DURATION_SECONDS` | Duracion maxima aceptada. Por defecto `300`. |
| `MAX_VIDEO_REACTIONS_PER_USER` | Numero maximo de reacciones distintas por usuario y video. |
| `VIDEO_ALLOWED_MIME_TYPES` | Lista JSON de MIME types permitidos. |
| `REDIS_URL` | URL de Redis usada por API y worker. |
| `VIDEO_PROCESSING_QUEUE_NAME` | Nombre de la cola RQ. |
| `VIDEO_PROCESSING_MAX_ATTEMPTS` | Reintentos maximos por job. |
| `VIDEO_PROCESSING_JOB_TIMEOUT_SECONDS` | Timeout maximo de cada job. |
| `PROXY_NETWORK_NAME` | Nombre de red externa para proxy inverso. |

Ejemplo minimo:

```env
APP_NAME=SpiderShare
APP_VERSION=1.0.0
APP_ENV=local
APP_DEBUG=true
APP_PORT=8000

MYSQL_DATABASE=spidershare
MYSQL_USER=spidershare
MYSQL_PASSWORD=spidershare_password
MYSQL_ROOT_PASSWORD=root_password
DATABASE_URL=mysql+pymysql://spidershare:spidershare_password@mysql:3306/spidershare

SECRET_KEY=change-me-in-real-env
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_PASSWORD=change-me-before-first-start

VIDEO_STORAGE_PATH=/app/storage/videos
MAX_VIDEO_SIZE_BYTES=524288000
MAX_VIDEO_DURATION_SECONDS=300
MAX_VIDEO_REACTIONS_PER_USER=2
VIDEO_ALLOWED_MIME_TYPES=["video/mp4","video/webm"]

REDIS_URL=redis://redis:6379/0
VIDEO_PROCESSING_QUEUE_NAME=video-processing
VIDEO_PROCESSING_MAX_ATTEMPTS=3
VIDEO_PROCESSING_JOB_TIMEOUT_SECONDS=900

STEAM_WEB_API_KEY=
STEAM_WEB_API_BASE_URL=https://api.steampowered.com
```

## Base de Datos y Migraciones

Alembic usa `DATABASE_URL` desde `config.settings`.

En Docker, la API ejecuta automaticamente:

```bash
alembic -c /app/alembic.ini upgrade head
python -m app.bootstrap.seed_super_admin
```

Crear una migracion:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api alembic revision --autogenerate -m "describe change"
```

Aplicar migraciones:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api alembic upgrade head
```

Ver historial:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec api alembic history
```

Migraciones actuales importantes:

- `users`: tabla de usuarios y columna `role`.
- `steam_games`: cache/persistencia de juegos Steam.
- `videos`: videos, categorias, tags, favoritos y reacciones.
- `video_variants`: salidas de procesado y miniaturas.
- `video_processing_errors`: historial de fallos de procesado por intento.
- `idempotency_records`: soporte para `Idempotency-Key`.

## Super Admin Inicial

En cada arranque Docker se ejecuta el seed de super admin.

Comportamiento:

- Si no hay `SUPER_ADMIN_USERNAME` ni `SUPER_ADMIN_PASSWORD`, no crea nada.
- Si solo una variable esta configurada, falla para evitar un estado incompleto.
- Si ya existe un `super_admin`, no crea otro.
- Si el username configurado ya existe con otro rol, no lo convierte.
- Si no hay super admin, crea uno con las credenciales configuradas.

## Autenticacion y Roles

El login devuelve un JWT bearer token.

Roles:

- `user`
- `admin`
- `super_admin`

Reglas principales:

- `admin` puede crear usuarios `user`.
- `super_admin` puede crear `admin` y `user`.
- Nadie crea `super_admin` desde `/auth/register`.
- Un usuario puede gestionarse a si mismo, salvo cambiar su propio `role` o `is_active`.
- Un rol solo puede gestionar usuarios de rango inferior.
- Usuarios inactivos no pueden autenticarse.

Header:

```http
Authorization: Bearer <token>
```

## Endpoints

### General

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| `GET` | `/health` | No | Estado basico. |
| `GET` | `/version` | No | Version configurada. |

### Auth

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | No | Login con JSON o form `username/password`. |
| `POST` | `/auth/register` | Admin | Crea un usuario permitido por rol. |
| `GET` | `/auth/me` | Si | Devuelve el usuario autenticado. |

### Users

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| `GET` | `/users` | Admin | Lista usuarios visibles para el admin actual. |
| `GET` | `/users/{user_id}` | Si | Obtiene un usuario si hay permiso. |
| `PATCH` | `/users/{user_id}` | Si | Actualiza username, display name, bio, rol o estado. |
| `PATCH` | `/users/{user_id}/password` | Si | Cambia password. Para uno mismo exige password actual. |
| `PUT` | `/users/{user_id}/avatar` | Si | Sube avatar. Maximo 2 MB. |
| `GET` | `/users/{user_id}/avatar` | Si | Descarga avatar. |
| `DELETE` | `/users/{user_id}/avatar` | Si | Elimina avatar. |
| `DELETE` | `/users/{user_id}` | Si | Elimina usuario si hay permiso. No elimina super admin. |

### Steam

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| `GET` | `/steam/users/{steam_id_or_vanity}/games` | No | Consulta juegos publicos de Steam y persiste juegos validos. |

Parametros:

- `include_played_free_games`: boolean, por defecto `true`.
- `language`: string, por defecto `english`.

`steam_id_or_vanity` acepta SteamID64, vanity name o URLs de Steam tipo `/id/...` y `/profiles/...`.

### Videos

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| `POST` | `/videos` | Si | Sube original, crea video `pending`, encola procesado y responde `201`. |
| `POST` | `/videos/{video_id}/processing/retry` | Super admin | Limpia salidas de procesado y reencola un video no completo. |
| `GET` | `/videos` | Publico | Lista videos visibles. Acepta token opcional para incluir privados accesibles. |
| `GET` | `/videos/{video_id}` | Publico | Detalle si el video es visible para el usuario actual o anonimo. |
| `GET` | `/videos/{video_id}/download` | Publico | Descarga original si hay permiso. |
| `GET` | `/videos/{video_id}/stream` | Publico | Sirve variante procesada o el original. |
| `GET` | `/videos/{video_id}/thumbnail` | Publico | Sirve miniatura JPEG si hay permiso. |
| `PATCH` | `/videos/{video_id}` | Si | Actualiza metadata si owner/admin/super admin. |
| `DELETE` | `/videos/{video_id}` | Si | Elimina video si owner/super admin. |
| `POST` | `/videos/{video_id}/favorite` | Si | Marca favorito. |
| `DELETE` | `/videos/{video_id}/favorite` | Si | Quita favorito. |
| `GET` | `/users/me/video-favorites` | Si | Lista favoritos del usuario autenticado. |
| `GET` | `/videos/{video_id}/reactions` | Publico | Conteos de reacciones visibles. |
| `POST` | `/videos/{video_id}/reactions` | Si | Crea o actualiza reaccion. |
| `DELETE` | `/videos/{video_id}/reactions` | Si | Elimina reaccion del usuario. |

Filtros de `GET /videos`:

- `title`: busqueda parcial.
- `tags`: lista de tags.
- `category_ids`: lista de UUID.
- `owner_id`: UUID del propietario.
- `limit`: `1..100`, por defecto `20`.
- `offset`: por defecto `0`.

`GET /videos` es publico. Si no hay token, solo devuelve videos visibles para anonimos. Si hay token valido, puede incluir videos registrados/privados segun permisos.

## Contrato de Videos

Las respuestas de video incluyen el propietario enriquecido:

```json
{
  "id": "video-uuid",
  "owner_id": "user-uuid",
  "owner": {
    "id": "user-uuid",
    "username": "alice",
    "display_name": "Alice"
  },
  "title": "Boss clip",
  "description": "Context",
  "processing_status": "pending",
  "playback_url": null,
  "download_url": "/videos/video-uuid/download"
}
```

Campos relevantes:

- `processing_status`: `pending`, `processing`, `ready`, `failed`.
- `playback_url`: aparece cuando el video esta `ready`.
- `download_url`: apunta al original.
- `thumbnail_url`: aparece cuando hay miniatura.
- `variants`: salidas procesadas por FFmpeg.
- `latest_processing_error`: ultimo fallo de procesado, si existe.
- `categories` y `tags`: metadata publica.
- `is_owner`, `can_edit`, `can_delete`, `is_favorite`, `reactions`: aparecen en detalle.

## Subida y Procesado de Videos

`POST /videos` recibe `multipart/form-data`:

- `file`: `video/mp4` o `video/webm` por defecto.
- `title`: requerido, maximo 255.
- `description`: opcional, maximo 5000.
- `is_registered_only`: boolean.
- `category_ids`: lista de UUID.
- `tags`: lista de strings, maximo configurado por `max_video_tags`.

Flujo:

1. La API valida usuario, metadata, MIME type, tamano y duracion.
2. Guarda el original en `VIDEO_STORAGE_PATH`.
3. Crea el video en base de datos con `processing_status=pending`.
4. Encola un job RQ con id `video-processing-{video_id}`.
5. Responde `201` sin esperar a FFmpeg.
6. El worker pasa el video a `processing`.
7. Si FFmpeg termina bien, guarda variantes/thumbnail y marca `ready`.
8. Si falla, marca `failed`, guarda una fila en `video_processing_errors` y deja logs con `video_id`, `job_id`, propietario, intento, duracion y error.

El worker debe compartir el mismo volumen de videos que la API.

Ver logs del worker:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f worker
```

Reejecutar worker manualmente dentro del stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec worker python -m app.workers.video_processing
```

Reintentar procesado como super admin:

```bash
curl -X POST http://localhost:8000/videos/<video_id>/processing/retry \
  -H "Authorization: Bearer <super-admin-token>"
```

El reintento solo acepta videos no completos (`pending`, `processing` o `failed`). Antes de reencolar, borra variantes, miniatura y temporales del video, conserva el original y deja el estado en `pending`.

## Idempotencia

`POST /videos` acepta:

```http
Idempotency-Key: <clave-unica-del-cliente>
```

Comportamiento:

- Misma key + mismo usuario + mismo payload: devuelve la misma respuesta guardada.
- Misma key + payload diferente: `409 Conflict`.
- Key en blanco: `400 Bad Request`.
- Request aun en proceso: `409 Conflict`.
- Error de servidor durante subida: se registra como failed para diagnostico.

La key se guarda por scope `videos.upload`, usuario y key. El payload se compara por hash de metadata y archivo.

## Logging

El logging se configura en `app/shared/infrastructure/logging.py`.

Cada linea incluye:

- `request_id`
- `client_ip`
- `auth_status`
- `user_id`
- `username`
- `user_role`
- `worker`
- `job_id`
- `video_id`
- `user_agent`

La API respeta `X-Request-ID` si llega y lo devuelve en la respuesta. Si no llega, genera uno nuevo.

Niveles:

- `INFO`: requests correctas, login/register correctos, subida, encolado, procesado terminado.
- `WARNING`: errores esperados de cliente, credenciales invalidas, conflictos de idempotencia.
- `ERROR`: respuestas `5xx`.
- `EXCEPTION`: fallos con traceback, como Redis caido, FFmpeg fallando o errores no controlados.

El worker usa `worker=jaimito_worker`, rellena `job_id` y `video_id`, registra `owner_id`, `username`, estado anterior/nuevo, duracion de transcodificacion y error, y ademas emite eventos:

- `event=jaimito.worker.waking_up`
- `event=jaimito.worker.redis_ready`
- `event=jaimito.worker.waiting`
- `event=jaimito.job.started`
- `event=jaimito.job.finished`
- `event=jaimito.job.failed`
- `event=jaimito.worker.shutting_down`

## Desarrollo Local sin Docker

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements/dev.txt
cp .env.example .env
```

Necesitas MySQL, Redis y FFmpeg accesibles desde tu maquina. Ajusta:

```env
DATABASE_URL=mysql+pymysql://...
REDIS_URL=redis://localhost:6379/0
VIDEO_STORAGE_PATH=./storage/videos
```

Migraciones:

```bash
alembic upgrade head
```

API:

```bash
uvicorn run:app --host 0.0.0.0 --port 8000 --reload --no-access-log
```

Worker:

```bash
python -m app.workers.video_processing
```

## Tests

Instalar dependencias:

```bash
python -m pip install -r requirements/dev.txt
```

Ejecutar todo:

```bash
pytest
```

Suites:

```bash
pytest -m unit
pytest -m http
pytest -m "unit or http"
```

Marcas:

- `unit`: tests puros sin DB, red ni `TestClient`.
- `http`: rutas FastAPI con overrides de dependencias.
- `integration`: reservado para DB, Docker o servicios externos reales.

Los tests actuales usan fakes para repositorios, storage, transcoder, cola y cliente Steam cuando corresponde.

Test de integracion Redis opt-in:

```bash
set REDIS_INTEGRATION_URL=redis://localhost:6379/0
pytest -m integration tests/integration/test_video_processing_queue.py
```

Si `REDIS_INTEGRATION_URL` no esta configurada, el test se salta.

## CI/CD

El changelog menciona despliegue mediante workflow GitHub Actions y webhook de Portainer. Si se usa ese flujo, el secreto esperado es:

```text
PORTAINER_WEBHOOK_URL
```

Antes de desplegar:

```bash
pytest -m "unit or http"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

## Permisos Resumidos

Videos:

- Anonimo: puede listar/ver/descargar/stream/thumbnail/reacciones de videos publicos.
- Usuario autenticado: puede ver videos publicos y videos registrados; puede subir, favorito y reaccionar.
- Owner: puede editar y borrar sus videos.
- Admin: puede editar videos segun reglas del dominio.
- Super admin: puede borrar videos.

Users:

- Admin ve y gestiona usuarios de rango inferior.
- Super admin ve y gestiona admins y usuarios.
- Un usuario puede gestionar su propio perfil, avatar y password, con restricciones sobre rol/estado.

Auth:

- Token invalido, usuario inexistente o usuario inactivo se tratan como credenciales no validas.

## Respuestas y Errores Habituales

- `400`: payload invalido, archivo vacio, MIME no permitido, `Idempotency-Key` en blanco.
- `401`: falta token o credenciales invalidas en rutas protegidas.
- `403`: usuario autenticado sin permiso.
- `404`: recurso no encontrado o no visible.
- `409`: conflicto de idempotencia, limite de reacciones o video no listo para variante procesada.
- `413`: video/avatar demasiado grande.
- `422`: validacion de FastAPI/Pydantic.
- `503`: cola de procesado no disponible al subir video.

Si `POST /videos` devuelve `503`, mira el log de la API con el mismo `request_id`; debe incluir `queue_backend`, `video_id`, `owner_id` y `error_type`.

## Checklist para Cambios

Cuando cambies modelos:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Cuando cambies variables:

- Actualiza `.env.example`.
- Actualiza `stack.env` en Portainer.
- Actualiza este README.

Cuando cambies videos/worker:

- Prueba `POST /videos`.
- Comprueba que responde `pending`.
- Mira logs de `worker`.
- Comprueba que pasa a `ready` o `failed`.
- Prueba `/stream`, `/thumbnail` y `/download`.

Cuando cambies contratos HTTP:

- Actualiza schemas.
- Actualiza tests HTTP.
- Actualiza este README.

## Pendiente Conocido

- Limpieza periodica de archivos huerfanos.
- Integracion con webhooks de Discord.
- Tests de integracion end-to-end con Redis/MySQL reales y worker ejecutando FFmpeg.
- Contador de visualizaciones.
- Asociacion opcional entre videos y juegos de Steam.
- Subida por chunks si los limites actuales de archivo/proxy se quedan cortos.
