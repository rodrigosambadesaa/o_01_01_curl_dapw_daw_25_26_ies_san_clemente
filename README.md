# Descargador multimedia — práctica O01.01 (DAW)

Proyecto educativo para descargar **imágenes, vídeos y audio** de contenidos públicos de X/Twitter, YouTube, Instagram, TikTok y otras redes sociales compatibles con los extractores. Mantiene el procesamiento de archivos HAR para recursos multimedia directos.

> **Aviso:** No garantiza descargar *todo* lo publicado en una plataforma. Un HAR solo incluye el contenido cargado por el navegador, no una cuenta entera; los vídeos HLS/DASH se descargan mejor por URL de publicación. El acceso privado, DRM, contenido eliminado, restricciones geográficas, cambios de API y límites de los servicios pueden impedir descargas. Respeta los derechos de autor, la privacidad y las condiciones legales aplicables.

## Requisitos

- Python 3.11 o superior.
- `python -m pip install -r requirements.txt`.
- Recomendado: `ffmpeg` instalado en PATH para fusionar vídeo y audio de distintas pistas (YouTube y otros).

## Uso

```bash
# Vídeo de YouTube
python o01_01_sambade_saa.py --url 'https://www.youtube.com/watch?v=ID'

# Publicación de X con fotos, GIF o vídeo: prueba dos extractores
python o01_01_sambade_saa.py --url 'https://x.com/usuario/status/ID'

# Publicaciones de Instagram y TikTok
python o01_01_sambade_saa.py --url 'https://www.instagram.com/p/ID/' --url 'https://www.tiktok.com/@usuario/video/ID'

# Captura HAR exportada desde DevTools (sin reutilizar cookies)
python o01_01_sambade_saa.py --har captura.har

# Limita archivos por extractor y peso por archivo
python o01_01_sambade_saa.py --url 'https://x.com/usuario/status/ID' --max-items 10 --max-size-mb 50

# Selecciona el extractor cuando sea necesario
python o01_01_sambade_saa.py --url 'https://x.com/usuario/status/ID' --backend gallery-dl
```

La salida se guarda por defecto en `multimedia_descargada/`, separada en `har/`, `gallery-dl/` y `yt-dlp/`. En modo automático, para X, Instagram y TikTok se prueban **ambos** extractores para ampliar formatos admitidos. Puede haber archivos duplicados entre extractores. Se admite `--output DIRECTORIO`.

Con `captura.har` en el directorio actual, también funciona el comando antiguo `python o01_01_sambade_saa.py` sin argumentos.

## Seguridad

- **Nunca** se publican los archivos HAR: pueden contener cookies, tokens de acceso y URLs privadas. No deben compartirse tampoco como logs de CI.
- El modo HAR **no reutiliza cabeceras, cookies ni tokens** de las solicitudes capturadas. Solo acepta recursos incrustados en el HAR o descargas HTTPS desde una lista controlada de dominios de multimedia; sin redirecciones automáticas y sin usar proxies del entorno.
- Valida host, protocolo, puertos, formatos MIME y límites por archivo; rechaza SVG y contenido HTML por seguridad.
- Las URLs de publicaciones se restringen a dominios reconocidos; los extractores externos pueden fallar o cambiar su funcionamiento, por lo que se deben mantener actualizados.
- No se ejecutan comandos de shell con URLs proporcionadas por usuarios y no se muestran errores con enlaces privados.
- No elude controles de acceso ni DRM, y no incorpora credenciales ni cookies al código fuente.

### Historial comprometido

El commit inicial contenía cookies `auth_token` y `ct0` en código. **Es necesario revocar las sesiones afectadas.** Para eliminar estos valores del historial remoto, se debe realizar una limpieza **coordinada** de todas las referencias, forks y copias existentes. No basta con eliminar el archivo del último commit. Ejemplo de trabajo local, tras crear un respaldo privado:

```bash
python -m pip install git-filter-repo
# Ejecutar en un clon espejo del repositorio, con todas las ramas y etiquetas.
git filter-repo --path o01_01_sambade_saa.py --replace-text ../replacements.txt
# replacements.txt debe contener expresiones exactas de las credenciales filtradas,
# NUNCA publicarse en Git y destruirse con seguridad tras la operación.
# Revisar el historial y coordinar un push --force --mirror solo después de verificar.
```

**Este repositorio todavía requiere limpieza del historial** hasta que se complete y verifique esa operación; la presente mejora evita reintroducir secretos.

## Pruebas

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
ruff check .
python -m pip_audit -r requirements.txt
```

GitHub Actions ejecuta pruebas, análisis estático y auditoría de dependencias en Python 3.11 y 3.13. Los tests no hacen descargas a las redes sociales reales: prueban validación, HAR, tipos MIME, límites y comandos externos con dobles de prueba. Para verificar plataformas reales se precisan pruebas manuales sobre URLs públicas autorizadas.

## Proyecto académico

Ampliación de la práctica O01.01 «Libraría requests e cURL» del ciclo DAW en IES San Clemente. Autoría: Rodrigo Sambade. Uso educativo.