# Changelog

Todas las mejoras notables de SpiderShare API se documentan en este archivo.

## [1.0.0] - 2026-05-23
### Añadido
- Primera release estable del backend de SpiderShare.
- Autenticación con JWT y gestión de roles (`user`, `admin`, `super_admin`).
- Gestión de usuarios: listar, obtener, actualizar, eliminar, cambiar password y avatar.
- Integración con Steam para consulta de juegos públicos.
- Módulo completo de videos: subida, listado, descarga, streaming, miniaturas, favoritos y reacciones.
- Documentación de endpoints en `README.md`.
- Endpoint de versión: `GET /version`.
- Soporte de configuración por variables de entorno y despliegue con Docker.

## Pendiente para versiones futuras
- Contador de visualizaciones.
- Asociaciones opcionales con Steam/juegos.
- Subida por chunks para archivos grandes y redes lentas.
- Procesamiento en cola para transcodificación.
- Limpieza automática de archivos huérfanos.
- Métricas de popularidad más avanzadas.
