# TODO
## Pendiente v2 / futuro

- Asociacion opcional con Steam/juegos.
- Limpieza periodica de archivos huerfanos o borrados fisicos fallidos.
- Mejoras futuras con Redis:
  - Progreso de procesado de video en tiempo real o casi real (`video:processing:{video_id}:progress`).
  - Blacklist de JWT para logout real y revocacion de tokens antes de su expiracion.
  - Contadores rapidos:
    - reproducciones de video;
    - descargas;
    - videos vistos recientemente.
  - Pub/Sub o eventos en tiempo real para avisar al backoffice de cambios de estado del worker/procesado.
- Integracion con webhooks de Discord para avisos de subidas y embedded de video en Discord:
  - Definir variables de entorno: `DISCORD_WEBHOOK_URL`, `DISCORD_NOTIFICATIONS_ENABLED` y URL publica/base de la API.
  - Crear puerto/servicio de dominio para notificaciones externas de videos.
  - Implementar proveedor HTTP para Discord Webhooks con timeouts, logs y manejo de errores no bloqueante.
  - Disparar aviso cuando un video queda `ready`, no al subirlo en `pending`.
  - Incluir en el mensaje: titulo, descripcion corta, autor, categorias/tags, thumbnail y enlaces a reproduccion/descarga.
  - Generar URL publica absoluta para `/videos/{video_id}/stream` o pagina de detalle si existe frontend.
  - Revisar compatibilidad de embed de Discord: si el stream autenticado o local no es publico, enviar enlace a detalle en lugar de esperar preview nativa.
  - Evitar publicar videos `is_registered_only` o permitirlo solo con flag/configuracion explicita.
  - Prevenir duplicados en reintentos del worker: idempotencia por `video_id` o evento notificado.
  - Anadir cola/reintento separado para notificaciones si Discord falla temporalmente.
  - Anadir tests unitarios del payload de Discord y del caso de uso al completar procesado.
  - Anadir tests de que fallos de Discord no cambian el estado `ready` del video.
  - Documentar configuracion en `.env.example` y README.
- Formula de popularidad mas rica si se agregan reacciones, visualizaciones o antiguedad.
