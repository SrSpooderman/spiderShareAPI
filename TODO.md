# TODO - orden de implementacion

Este documento esta ordenado para avanzar sin bloquearse. Primero van las tareas que se pueden implementar ya. Despues aparece el punto donde hacen falta decisiones pendientes. Al final queda la lista de tareas que se podran implementar cuando esas preguntas esten respondidas.

## 1. Robustez de API

Estas tareas se pueden hacer ya, antes del modulo de videos.

1. Gestionar hashes de password invalidos.
   - `PasswordHasher.verify_password` puede lanzar error si el hash guardado no es bcrypt valido.
   - Hacer que devuelva `False` en vez de provocar un `500`.

2. Validar campos de entrada.
   - Anadir limites y minimos con Pydantic para `username`, `password`, `new_password`, `display_name` y `bio`.
   - Evitar strings vacios o demasiado largos que puedan acabar en errores SQL.
   - Normalizar/recortar `username` si se decide permitir espacios accidentales.

3. Capturar conflictos reales de base de datos.
   - El registro y el cambio de username comprueban duplicados antes de guardar, pero dos requests simultaneas pueden saltarse esa comprobacion.
   - Capturar `IntegrityError` y devolver `409 Conflict`.

4. Revisar borrado de usuarios `super_admin`.
   - Ahora un `super_admin` podria borrarse a si mismo.
   - Decidir si se bloquea siempre, o como minimo impedir borrar el ultimo `super_admin`.

5. Actualizar `last_login_at`.
   - El campo existe pero no se actualiza al hacer login.
   - Guardar la fecha/hora de login correcto.

6. Validar avatares por contenido real.
   - El endpoint valida `content_type`, que lo envia el cliente y se puede falsificar.
   - Validar tambien la firma real del archivo despues de leer los bytes.

7. Aclarar endpoint de juegos de Steam.
   - La ruta parece publica por nombre/documentacion, pero exige usuario autenticado.
   - Decidir si debe ser publica o protegida, y alinear codigo y README.

8. Revisar migracion que borra `user_steam_accounts`.
   - Confirmar que perder esos vinculos es intencionado.
   - Hacer backup antes de aplicar en produccion.

## 2. Logging y observabilidad

Estas tareas tambien se pueden hacer ya.

1. Crear configuracion central de logging para toda la API.
2. Usar logs legibles en consola para desarrollo.
3. Incluir nivel, timestamp, modulo, metodo, ruta y status code.
4. Anadir `request_id` si se implementa middleware para ello.
5. Registrar errores con stacktrace cuando proceda.
6. Evitar `print` sueltos y mensajes basicos dificiles de rastrear.
7. Separar niveles:
   - `INFO` para arranque y requests importantes.
   - `WARNING` para casos recuperables.
   - `ERROR` para fallos.
8. Revisar logs de Uvicorn/FastAPI para que no queden duplicados ni desordenados.
9. Opcional: preparar formato JSON para produccion si Portainer o el sistema de logs lo aprovecha.

## 3. Videos - decisiones ya cerradas

Estas reglas ya estan decididas y se pueden usar para disenar el modulo.

### Producto

- Los videos son publicos por defecto.
- El propietario puede marcar un video como "solo usuarios registrados".
- Los enlaces directos usan el UUID del video y no caducan.
- Los enlaces respetan los permisos del video:
  - Video publico: visible sin login.
  - Video solo registrados: visible solo con login.
- El propietario o un `admin` pueden editar un video despues de subirlo.
- El propietario o un `super_admin` pueden borrar un video.
- El campo `edited` debe pasar a `true` despues de cualquier edicion.
- El campo `edited_at` debe guardar la fecha de la ultima edicion.

### Permisos

- Propietario:
  - Ver su video.
  - Editar su video.
  - Borrar su video.
  - Cambiar si el video es publico o solo registrados.
- Usuario anonimo:
  - Ver videos publicos.
  - No puede marcar favoritos ni reaccionar.
- Usuario registrado:
  - Ver videos publicos.
  - Ver videos marcados como solo registrados.
  - Marcar favoritos.
  - Reaccionar.
- `admin`:
  - Puede editar videos ajenos.
  - No puede borrar videos ajenos.
- `super_admin`:
  - Puede editar videos ajenos.
  - Puede borrar videos ajenos.
- Los favoritos son publicos como contador agregado en el video.

### Metadata

- Campos obligatorios al subir:
  - `title`
  - `description`
- `description` sera el contexto del clip. No usar `context` separado en v1.
- Un clip puede tener varias categorias.
- Los tags son libres y creados por usuarios.
- Maximo de tags configurable por `.env`; por defecto `6`.
- La vista debe mostrar:
  - Clip reproducible.
  - Titulo.
  - Fecha.
  - Categorias.
  - Tags.
  - Propietario.
  - Boton para copiar enlace directo.
  - Modo edicion si el usuario logeado es propietario o admin.
  - Description/contexto.
  - Boton de favoritos.
  - Reacciones agregadas.
  - Contador publico de favoritos.

### Reproduccion y archivo

- Debe existir opcion de descargar el clip.
- Deben guardarse `width`, `height` y `aspect_ratio`.
- El backend debe calcular el aspect ratio.
- Ratios validos: `4:3`, `16:9`, `21:9`.
- Tamano maximo configurable desde `.env`.
- Duracion maxima configurable desde `.env`.
- Aceptar formatos de video reproducibles en web.
- Guardar el nombre original del archivo salvo que se pase un nombre por parametro.
- El identificador interno del video debe ser UUID.

### Transcodificacion

- Decision cerrada: transcodificar.
- Objetivo:
  - Convertir videos a formato web estandar.
  - Calcular metadata real.
  - Generar thumbnail.
  - Normalizar compatibilidad de reproduccion.
- Consecuencia tecnica:
  - Se necesitara FFmpeg u otro procesador.
  - Puede hacer falta estado `processing`.
  - Puede hacer falta una cola de trabajos si el procesamiento tarda.

### Vista principal y busqueda

- `GET /videos` devuelve clips visibles para el usuario actual.
- Debe estar paginado desde v1.
- Orden por defecto: popularidad.
- Filtros iniciales:
  - Titulo/nombre.
  - Tags.
  - Categorias.
  - Usuario creador.
- Busqueda por texto: titulo.
- La popularidad debe tener en cuenta favoritos.

### Favoritos

- Un usuario registrado puede marcar como favorito cualquier clip visible.
- Debe existir endpoint para listar "mis favoritos".
- La lista de favoritos debe estar paginada.
- Los favoritos suman al contador publico del video.
- Los favoritos afectan a la popularidad.

### Reacciones

- Existiran reacciones desde v1.
- Los tipos exactos se declararan mas adelante, probablemente un par de emojis.
- Un usuario solo puede tener un tipo de reaccion por clip.
- La API mostrara solo el numero por tipo de reaccion, no la lista completa de usuarios.
- El usuario puede borrar o cambiar su reaccion.

### Compartir

- El enlace directo usa `video_uuid`.
- No caduca.
- No se regenera.
- No se desactiva en v1.
- Si el video esta marcado como solo registrados, el enlace exige login.

## 4. Videos - implementar ya sin mas decisiones

Estas tareas no dependen de las preguntas pendientes.

1. Crear estructura del modulo.

```text
app/modules/videos/
  domain/
    video.py
    ports.py
  application/
    list_videos.py
    get_video.py
    update_video.py
    delete_video.py
    favorite_video.py
    react_to_video.py
  entrypoints/
    routes.py
    schemas.py
  infrastructure/
    models.py
    mappers.py
    repository.py
  wiring.py
```

2. Anadir settings del modulo en `config/settings.py`.
   - `max_video_size_bytes`
   - `max_video_duration_seconds`
   - `max_video_tags = 6`
   - `video_allowed_mime_types`
   - `video_storage_path` si no se reutiliza `VIDEO_STORAGE_PATH`.

3. Crear dominio base.
   - Entidad `Video`.
   - Entidad `VideoCreate`.
   - Entidad `VideoCategory`.
   - Entidad `VideoTag`.
   - Entidad `VideoFavorite`.
   - Entidad `VideoReaction`.
   - Enum/valor de `aspect_ratio`: `4:3`, `16:9`, `21:9`.
   - Campo `is_registered_only`.
   - Campo `edited`.
   - Campo `edited_at`.
   - Campo `processing_status`: recomendado por transcodificacion.

4. Crear reglas de permisos.
   - Ver video publico: anonimos y logeados.
   - Ver video solo registrados: usuarios logeados.
   - Editar: propietario o `admin`/`super_admin`.
   - Borrar: propietario o `super_admin`.
   - Favorito/reaccion: solo usuario logeado.

5. Crear modelos SQLAlchemy.
   - `videos`
   - `video_categories`
   - `video_category_assignments`
   - `video_tags`
   - `video_tag_assignments`
   - `video_favorites`
   - `video_reactions`

6. Crear mappers model/domain.
7. Crear repositorio SQLAlchemy.
8. Crear migracion Alembic para las tablas anteriores.
9. Crear schemas Pydantic de respuesta y payloads de metadata.
10. Crear casos de uso que no dependen del archivo todavia.
    - `ListVideos`
    - `GetVideo`
    - `UpdateVideo`
    - `DeleteVideo` solo borrado logico/metadata hasta decidir borrado fisico.
    - `FavoriteVideo`
    - `ReactToVideo`

11. Crear rutas que no dependen del contrato de subida/Node.
    - `GET /videos`
    - `GET /videos/{video_id}`
    - `PATCH /videos/{video_id}`
    - `DELETE /videos/{video_id}`
    - `POST /videos/{video_id}/favorite`
    - `DELETE /videos/{video_id}/favorite`
    - `GET /users/me/video-favorites`
    - `GET /videos/{video_id}/reactions`
    - `POST /videos/{video_id}/reactions`
    - `DELETE /videos/{video_id}/reactions`

12. Implementar paginacion y filtros.
    - Por titulo.
    - Por tags.
    - Por categorias.
    - Por usuario creador.

13. Implementar orden inicial de popularidad con formula temporal.
    - Usar `favorite_count` descendente.
    - Dejar TODO para formula final.

14. Crear tests.
    - Permisos.
    - Paginacion.
    - Filtros.
    - Favoritos.
    - Reacciones.
    - Edicion y `edited=true`.
    - Borrado por propietario y `super_admin`.
    - Bloqueo de borrado por `admin`.

## 5. Punto de bloqueo: preguntas a responder

Responder estas preguntas antes de implementar subida, transcodificacion real, playback y borrado fisico.

1. Que valor por defecto tendra `MAX_VIDEO_SIZE_BYTES`?
2. Que valor por defecto tendra `MAX_VIDEO_DURATION_SECONDS`?
3. Que mime types concretos se aceptaran como "video reproducible en web"?
4. Si un video no es `4:3`, `16:9` o `21:9`, se rechaza, se adapta con barras o se recorta/transcodifica?
5. El backend Node.js guarda y sirve archivos, o solo sirve archivos que guarda FastAPI?
6. Cual sera el contrato exacto entre FastAPI y Node.js para subir/servir clips?
7. Como sera la subida por chunks?
   - Endpoint de iniciar subida.
   - Endpoint de subir chunk.
   - Endpoint de finalizar subida.
   - Identificador de upload temporal.
8. Hace falta borrar el archivo fisico cuando se borra el registro?
9. Que tipos exactos de reaccion se aceptaran en v1?
10. Que formula exacta define popularidad?
11. Hace falta contador de visualizaciones?
12. Hace falta asociar videos con Steam/juegos en el futuro?

## 6. Implementar despues de responder preguntas

Estas tareas dependen de las respuestas anteriores.

1. Implementar subida real de videos.
   - Directa o por chunks segun decision final.
   - Validacion de tamano maximo.
   - Validacion de mime type permitido.
   - Persistencia de archivo o envio a Node.js.

2. Implementar contrato con backend Node.js.
   - URL/base de Node en `.env`.
   - Cliente/adaptador desde FastAPI.
   - Manejo de errores de Node.
   - Tests con fake del backend Node.

3. Implementar transcodificacion.
   - Integrar FFmpeg u otro procesador.
   - Convertir a formato web final.
   - Generar thumbnail.
   - Calcular duracion real.
   - Calcular `width`, `height` y `aspect_ratio`.
   - Manejar estado `processing`, `ready`, `failed`.

4. Implementar politica para ratios no validos.
   - Rechazar, adaptar con barras o recortar/transcodificar.

5. Implementar descarga/playback.
   - `GET /videos/{video_id}/download`.
   - `playback_url` devuelta por FastAPI o Node.js segun contrato.

6. Implementar borrado fisico.
   - Borrar archivo original.
   - Borrar archivo transcodificado.
   - Borrar thumbnail.
   - Coordinar borrado con Node.js si aplica.

7. Cerrar reacciones exactas.
   - Definir lista permitida.
   - Validar `reaction_type`.
   - Actualizar tests.

8. Cerrar formula de popularidad.
   - Favoritos.
   - Reacciones.
   - Visualizaciones si se decide incluirlas.
   - Antiguedad si se decide ponderar por fecha.

9. Implementar contador de visualizaciones si se decide incluirlo.

10. Implementar asociacion con Steam/juegos si se decide incluirla.

## 7. Respuesta sugerida para `GET /videos/{video_id}`

```json
{
  "id": "uuid",
  "title": "Clip - Titulo",
  "description": "Clip - Contexto",
  "categories": [
    {
      "id": "uuid",
      "name": "Categoria"
    }
  ],
  "tags": ["tag-1", "tag-2"],
  "owner": {
    "id": "uuid",
    "username": "usuario"
  },
  "created_at": "datetime",
  "updated_at": "datetime",
  "edited_at": "datetime | null",
  "edited": true,
  "share_url": "string",
  "playback_url": "string",
  "download_url": "string",
  "thumbnail_url": "string",
  "aspect_ratio": "16:9",
  "width": 1920,
  "height": 1080,
  "processing_status": "ready",
  "is_owner": true,
  "can_edit": true,
  "can_delete": false,
  "is_favorite": false,
  "favorite_count": 12,
  "is_registered_only": false,
  "reactions": [
    {
      "type": "like",
      "count": 3
    }
  ]
}
```
