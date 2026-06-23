# TODO

## Prioridad alta

- [API] "categorias de video": "validar que `category_ids` existan antes de crear o editar videos y devolver `422` con ids invalidos en vez de dejar que falle la FK"
- [API] "categorias SteamGridDB": "anadir auditoria al importar categorias desde SteamGridDB: actor, steam_appid, steamgriddb_game_id, thumbnails encontrados y resultado"
- [API] "subida de videos": "persistir un evento operativo cuando se recibe el upload: `video.upload.received` con video_id, owner_id, filename, content_type, size_bytes e idempotency_key_hash"
- [API] "subida de videos": "persistir un evento operativo cuando se encola procesado: `video.processing.enqueued` con video_id, queue_name, job_id si RQ lo expone y queue_backend"
- [API] "subida bulk": "decidir contrato final para bulk: limite por lote, respuesta parcial vs todo-o-nada, idempotencia por lote y errores por indice"
- [LOGGING] "formato de logs": "migrar logs de texto `event=... key=value` a JSON estructurado configurable por entorno, manteniendo consola legible en local"
- [LOGGING] "correlacion": "propagar `request_id` a jobs de procesado y guardarlo en `worker_events` para unir API upload -> queue -> worker -> resultado"
- [WORKER] "procesado de video": "registrar evento `video.processing.started` cuando el caso de uso marca el video como processing"
- [WORKER] "procesado de video": "registrar metadata de FFmpeg/ffprobe en eventos: duration_seconds, width, height, aspect_ratio, variants_count, output_size_bytes"
- [WORKER] "errores de procesado": "normalizar tipos de error (`ffprobe_failed`, `ffmpeg_failed`, `storage_missing`, `repository_error`, `unknown`) para filtros del backoffice"
- [BACKOFFICE] "detalle de video": "mostrar timeline completo por video mezclando upload, enqueue, processing.started, completed/failed, retry y delete"
- [BACKOFFICE] "eventos worker": "anadir filtros por event_type, date_from/date_to, owner_id y request_id ademas de level/video_id/job_id"
- [BACKOFFICE] "auditoria": "mostrar metadata expandible en cada entrada de audit, no solo actor/action/entity/result"

## Prioridad media

- [API] "audit trail": "registrar acciones sensibles fuera de admin routes: crear categoria, importar categoria Steam, editar video, borrar video, retry, requeue, delete queue job"
- [API] "errores HTTP": "unificar payload de errores con `code`, `detail`, `request_id` y `metadata` para facilitar soporte desde backoffice"
- [API] "SteamGridDB": "guardar `steamgriddb_asset_id`, score y author de los grids elegidos para trazabilidad de thumbnails"
- [API] "SteamGridDB": "permitir refrescar thumbnails de una categoria Steam sin recrearla"
- [API] "SteamGridDB": "permitir elegir manualmente entre varios grids verticales/horizontales antes de importar"
- [API] "categorias custom": "permitir subir imagen vertical/horizontal propia y servirla desde storage en vez de depender solo de URL externa"
- [API] "videos": "anadir contador de reproducciones y descargas con eventos `video.stream.opened` y `video.download.opened`"
- [API] "videos": "incluir categorias y tags en las respuestas admin de video list/detail para mejorar exploracion operativa"
- [WORKER] "progreso": "publicar progreso aproximado en Redis (`video:processing:{video_id}:progress`) y persistir checkpoints importantes"
- [WORKER] "reintentos": "registrar numero de intento real de RQ y enlazarlo con `video_processing_errors.attempt`"
- [WORKER] "limpieza": "crear job periodico de limpieza de archivos huerfanos, outputs temporales y borrados fisicos fallidos"
- [BACKOFFICE] "dashboard": "anadir tarjetas de salud operativa: uploads ultimas 24h, fallos ultimas 24h, tiempo medio de procesado, cola pendiente"
- [BACKOFFICE] "dashboard": "mostrar ultimos eventos criticos con acceso directo al video/job"
- [BACKOFFICE] "videos": "anadir filtros por categoria, tag, owner, fechas, duracion y estado de error"
- [BACKOFFICE] "categorias": "crear pantalla de gestion de categorias con source, appid, thumbnails, numero de videos y acciones de refresco"
- [BACKOFFICE] "raw logs": "permitir copiar linea/log JSON y filtrar por request_id/job_id/video_id"
- [INFRA] "observabilidad": "exponer endpoint admin de diagnostico de configuracion no sensible: storage path, queue name, limites, SteamGridDB configured true/false"

## Prioridad baja

- [API] "popularidad": "mejorar formula usando favoritos, reacciones, reproducciones, descargas y antiguedad"
- [API] "notificaciones Discord": "definir variables `DISCORD_WEBHOOK_URL`, `DISCORD_NOTIFICATIONS_ENABLED` y URL publica/base de API"
- [API] "notificaciones Discord": "crear puerto/servicio de dominio para notificaciones externas de videos"
- [API] "notificaciones Discord": "implementar proveedor HTTP para Discord Webhooks con timeout, logs y errores no bloqueantes"
- [WORKER] "notificaciones Discord": "disparar aviso cuando un video queda `ready`, nunca al subirlo en `pending`"
- [WORKER] "notificaciones Discord": "evitar publicar videos `is_registered_only` salvo flag/configuracion explicita"
- [WORKER] "notificaciones Discord": "prevenir duplicados en reintentos con idempotencia por video_id/evento"
- [WORKER] "notificaciones Discord": "anadir cola/reintento separado para notificaciones si Discord falla temporalmente"
- [BACKOFFICE] "notificaciones Discord": "mostrar estado de notificacion por video: pendiente, enviada, fallida, omitida por privacidad"
- [TESTS] "trazabilidad": "tests unitarios para payloads de eventos operativos y auditoria"
- [TESTS] "trazabilidad": "tests HTTP que comprueben que operaciones admin generan audit entries y worker_events esperados"
- [TESTS] "notificaciones Discord": "tests del payload Discord y de que sus fallos no cambian estado `ready`"
- [DOCS] "logging": "documentar catalogo de event_type, metadata esperada y como depurar por request_id/video_id/job_id"
- [DOCS] "operacion": "documentar playbook de incidencias: Redis caido, FFmpeg falla, storage missing, upload 413, SteamGridDB 401/404"
