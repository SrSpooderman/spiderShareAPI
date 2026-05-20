# SpiderShare API

API backend de SpiderShare construida con FastAPI, SQLAlchemy, Alembic y MySQL. El proyecto esta organizado por modulos de negocio para que sea facil anadir nuevas areas sin mezclar rutas, casos de uso, dominio e infraestructura.

Ahora mismo incluye:

- Autenticacion con JWT.
- Gestion de usuarios, roles, passwords y avatares.
- Integracion con Steam para consultar juegos publicos.
- Migraciones automaticas con Alembic.
- Seed automatico de super admin.
- Tests unitarios y HTTP aislados de base de datos y red.
- Deploy mediante webhook de Portainer despues de pasar tests en CI/CD.

Los videos todavia no estan implementados como modulo completo. El proyecto ya reserva `VIDEO_STORAGE_PATH` y volumen de almacenamiento para esa futura parte.

## Stack

- Python 3.12 en Docker.
- FastAPI.
- Uvicorn.
- Pydantic Settings.
- SQLAlchemy.
- Alembic.
- MySQL 8.4.
- python-jose para JWT.
- bcrypt para passwords.
- Pytest + HTTPX para tests.

## Estructura

```text
app/
  bootstrap/                 Arranque de FastAPI, routers y seed inicial.
  modules/
    auth/
      application/           Casos de uso: register, login, password hashing.
      entrypoints/           Rutas y schemas HTTP.
      infrastructure/        JWT.
      wiring.py              Dependencias FastAPI del modulo.
    users/
      domain/                Entidades, roles y puertos.
      entrypoints/           Rutas y schemas HTTP.
      infrastructure/        Modelos SQLAlchemy, mappers y repositorio.
      wiring.py
    steam/
      application/           Casos de uso de Steam.
      domain/                Entidades y puertos.
      entrypoints/           Rutas y schemas HTTP.
      infrastructure/        Modelos, mappers y repositorios.
      wiring.py
  shared/
    infrastructure/
      db/                    Base SQLAlchemy y sesiones.
      providers/
        steam/               Cliente de Steam Web API.
        storage/             Preparado para almacenamiento de videos.
config/                      Settings.
migrations/                  Alembic.
requirements/                Dependencias runtime y dev.
tests/                       Tests unitarios y HTTP.
```

La idea principal es mantener cada modulo con estas capas:

- `domain`: reglas puras, entidades y puertos.
- `application`: casos de uso.
- `entrypoints`: HTTP, schemas y traduccion de errores a status codes.
- `infrastructure`: SQLAlchemy, mappers y adaptadores externos.
- `wiring.py`: dependencias de FastAPI.

## Entornos

El proyecto usa variables de entorno desde `.env` en local y `stack.env` cuando se ejecuta como stack en Portainer. Los compose leen ambos si existen.

### Desarrollo

En desarrollo se usa `docker-compose.dev.yml`, que monta el codigo local dentro del contenedor y arranca Uvicorn con `--reload`.

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

La API queda en:

```text
http://localhost:8000
```

Documentacion interactiva de FastAPI:

```text
http://localhost:8000/docs
```

Healthcheck:

```bash
curl http://localhost:8000/health
```

### Produccion o Portainer

En produccion se usa `docker-compose.yml`. El contenedor:

1. Espera a que MySQL este healthy.
2. Ejecuta migraciones: `alembic upgrade head`.
3. Siembra el super admin si corresponde.
4. Arranca Uvicorn.

Comando equivalente:

```bash
docker compose up --build -d
```

En Portainer, define las variables en `stack.env` o en el editor de variables del stack. Como minimo revisa:

```env
APP_ENV=production
APP_DEBUG=false
APP_PORT=8000

MYSQL_DATABASE=spidershare
MYSQL_USER=spidershare
MYSQL_PASSWORD=change-me
MYSQL_ROOT_PASSWORD=change-me-too

DATABASE_URL=mysql+pymysql://spidershare:change-me@mysql:3306/spidershare

SECRET_KEY=change-this-to-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15

SUPER_ADMIN_USERNAME=admin
SUPER_ADMIN_PASSWORD=change-me-before-first-start

STEAM_WEB_API_KEY=
STEAM_WEB_API_BASE_URL=https://api.steampowered.com

VIDEO_STORAGE_PATH=/app/storage/videos
```

Importante: cambia `SECRET_KEY`, passwords de MySQL y credenciales del super admin antes de desplegar.

## Variables de entorno

| Variable | Uso |
| --- | --- |
| `APP_NAME` | Nombre de la aplicacion. |
| `APP_ENV` | Entorno logico: `local`, `development`, `production`, etc. |
| `APP_DEBUG` | Flag de debug. |
| `APP_PORT` | Puerto expuesto por Docker. |
| `DATABASE_URL` | URL SQLAlchemy usada por app y Alembic. |
| `VIDEO_STORAGE_PATH` | Ruta donde se guardaran videos cuando el modulo exista. |
| `SECRET_KEY` | Clave para firmar JWT. Obligatoria. |
| `JWT_ALGORITHM` | Algoritmo JWT. Por defecto `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duracion del token de acceso. |
| `SUPER_ADMIN_USERNAME` | Usuario inicial con rol `super_admin`. |
| `SUPER_ADMIN_PASSWORD` | Password inicial del super admin. |
| `STEAM_WEB_API_KEY` | API key de Steam. Necesaria para endpoints que consultan Steam real. |
| `STEAM_WEB_API_BASE_URL` | Base URL de Steam Web API. |

## Base de datos y migraciones

Alembic toma `DATABASE_URL` desde `config.settings`.

Crear una migracion despues de cambiar modelos:

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

En el arranque normal con Docker, `alembic upgrade head` se ejecuta automaticamente.

## Super admin inicial

En cada arranque Docker se ejecuta:

```bash
python -m app.bootstrap.seed_super_admin
```

Comportamiento:

- Si no hay `SUPER_ADMIN_USERNAME` ni `SUPER_ADMIN_PASSWORD`, no hace nada.
- Si solo una de las dos variables existe, falla para evitar configuraciones incompletas.
- Si ya existe un usuario `super_admin`, no crea otro.
- Si el username configurado ya existe, no lo convierte automaticamente.
- Si no hay super admin, crea uno con el username y password configurados.

## Autenticacion y roles

El login devuelve un JWT bearer token.

Roles actuales:

- `user`
- `admin`
- `super_admin`

Reglas principales:

- `admin` puede crear usuarios `user`.
- `super_admin` puede crear `admin` y `user`.
- Nadie puede crear otro `super_admin` desde `/auth/register`.
- Un usuario puede gestionarse a si mismo, salvo cambiar su propio `role` o `is_active`.
- Un rol solo puede gestionar usuarios de rango inferior.

## Endpoints principales

### General

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| `GET` | `/health` | Estado basico de la API. |

### Auth

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| `POST` | `/auth/login` | Login con username y password. |
| `POST` | `/auth/register` | Crear usuario. Requiere admin. |
| `GET` | `/auth/me` | Devuelve el usuario autenticado. |

### Users

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| `GET` | `/users` | Lista usuarios visibles para el admin actual. |
| `GET` | `/users/{user_id}` | Obtiene un usuario si hay permiso. |
| `PATCH` | `/users/{user_id}` | Actualiza username, perfil, rol o estado. |
| `PATCH` | `/users/{user_id}/password` | Cambia password. |
| `PUT` | `/users/{user_id}/avatar` | Sube avatar. Maximo 2 MB. |
| `GET` | `/users/{user_id}/avatar` | Descarga avatar. |
| `DELETE` | `/users/{user_id}/avatar` | Elimina avatar. |
| `DELETE` | `/users/{user_id}` | Elimina usuario. |

### Steam

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| `GET` | `/steam/users/{steam_id_or_vanity}/games` | Consulta juegos publicos de Steam. |

`steam_id_or_vanity` acepta SteamID64, vanity name o URLs de Steam tipo `/id/...` y `/profiles/...`.

## Tests

Instalar dependencias de desarrollo:

```bash
python -m pip install -r requirements/dev.txt
```

Ejecutar todos los tests:

```bash
pytest
```

Suite rapida actual:

```bash
pytest -m "unit or http"
```

Solo unitarios:

```bash
pytest -m unit
```

Solo HTTP con FastAPI `TestClient`:

```bash
pytest -m http
```

Marcas disponibles:

- `unit`: tests puros sin DB, red ni `TestClient`.
- `http`: rutas FastAPI con overrides de dependencias.
- `integration`: reservado para tests con DB, migraciones, Docker o servicios externos.

Los tests actuales no necesitan MySQL, Docker, Steam real ni `STEAM_WEB_API_KEY`.

## CI/CD

El workflow esta en:

```text
.github/workflows/deploy.yml
```

Flujo actual:

1. En cada push a `main`, GitHub Actions ejecuta tests.
2. Si pasan, dispara el webhook de Portainer.
3. Si fallan, no hay deploy.

Tambien se puede lanzar manualmente con `workflow_dispatch` desde GitHub Actions.

Secret necesario:

```text
PORTAINER_WEBHOOK_URL
```

## Desarrollo local sin Docker

Si quieres ejecutar fuera de Docker:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/dev.txt
cp .env.example .env
```

Necesitas ajustar `DATABASE_URL` para apuntar a una base accesible desde tu maquina.

Aplicar migraciones:

```bash
alembic upgrade head
```

Arrancar API:

```bash
uvicorn run:app --host 0.0.0.0 --port 8000 --reload
```

## Como anadir un modulo nuevo

Usa la misma forma que `users` o `steam`.

```text
app/modules/nuevo_modulo/
  domain/
    ports.py
    entidad.py
  application/
    caso_de_uso.py
  entrypoints/
    routes.py
    schemas.py
  infrastructure/
    models.py
    mappers.py
    repository.py
  wiring.py
```

Pasos recomendados:

1. Define entidades y reglas en `domain`.
2. Define puertos en `domain/ports.py`.
3. Implementa casos de uso en `application`.
4. Crea modelos SQLAlchemy y mappers en `infrastructure`.
5. Implementa repositorios contra SQLAlchemy.
6. Expone rutas en `entrypoints/routes.py`.
7. Declara dependencias en `wiring.py`.
8. Incluye el router en `app/bootstrap/app_factory.py`.
9. Crea una migracion Alembic.
10. Anade tests unitarios primero y HTTP despues.

## Futuro modulo de videos

Ya existe preparacion minima:

- `VIDEO_STORAGE_PATH`.
- Volumen Docker `video_storage`.
- Carpeta `storage/videos`.
- Archivo reservado `app/shared/infrastructure/providers/storage/video_storage.py`.

Una implementacion limpia podria ser:

```text
app/modules/videos/
  domain/
    video.py
    ports.py
  application/
    upload_video.py
    list_videos.py
    get_video.py
    delete_video.py
  entrypoints/
    routes.py
    schemas.py
  infrastructure/
    models.py
    mappers.py
    repository.py
```

Decisiones pendientes para videos:

- Tamano maximo de archivo.
- Formatos permitidos.
- Si el archivo se sirve desde FastAPI, Nginx, Portainer volume o storage externo.
- Si se guarda metadata en DB: propietario, nombre, mime type, tamano, estado, fechas.
- Si habra procesamiento/transcodificacion.
- Politica de permisos: videos propios, compartidos, admin, publico/privado.

## Checklist para cambios

Antes de abrir PR o desplegar:

```bash
pytest -m "unit or http"
```

Si cambias modelos:

```bash
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

Si cambias variables:

- Actualiza `.env.example`.
- Actualiza `stack.env` en Portainer.
- Revisa este README.

## Comandos utiles

Arrancar dev:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

Arrancar produccion local:

```bash
docker compose up --build -d
```

Ver logs:

```bash
docker compose logs -f api
```

Entrar al contenedor API:

```bash
docker compose exec api sh
```

Parar servicios:

```bash
docker compose down
```

Parar y borrar volumenes:

```bash
docker compose down -v
```
