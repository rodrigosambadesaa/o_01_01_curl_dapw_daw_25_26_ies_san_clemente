"""Descarga de medios de HAR locales y publicaciones públicas de redes sociales.

El HAR es entrada no confiable: nunca se reenvían cookies ni cabeceras capturadas.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

import requests

MAX_HAR_BYTES = 20 * 1024 * 1024
DEFAULT_MAX_FILE = 100 * 1024 * 1024
DEFAULT_MAX_ITEMS = 20

# Los límites de dominio deben coincidir con el host o con un subdominio real.
POST_HOSTS = (
    "x.com", "twitter.com", "youtube.com", "youtu.be", "instagram.com",
    "tiktok.com", "facebook.com", "fb.watch", "threads.net", "reddit.com",
    "redd.it", "pinterest.com", "pin.it", "vimeo.com", "dailymotion.com",
    "twitch.tv", "bsky.app", "flickr.com", "soundcloud.com",
)
MEDIA_HOSTS = POST_HOSTS + (
    "twimg.com", "googlevideo.com", "ytimg.com", "cdninstagram.com",
    "fbcdn.net", "tiktokcdn.com", "tiktokv.com", "muscdn.com",
)
MEDIA_EXTENSIONS = {
    "image/jpeg": ".jpg", "image/png": ".png", "image/gif": ".gif",
    "image/webp": ".webp", "image/avif": ".avif", "image/bmp": ".bmp",
    "video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov",
    "video/x-matroska": ".mkv", "video/ogg": ".ogv",
    "audio/mpeg": ".mp3", "audio/mp4": ".m4a", "audio/wav": ".wav",
    "audio/x-wav": ".wav", "audio/ogg": ".ogg", "audio/webm": ".weba",
    "audio/flac": ".flac",
}


def trusted_host(host: str, domains: tuple[str, ...]) -> bool:
    host = host.lower().rstrip(".")
    return any(host == domain or host.endswith("." + domain) for domain in domains)


def validate_url(url: str, domains: tuple[str, ...]) -> str:
    """Bloquea URL no HTTPS, credenciales embebidas, IP y dominios engañosos."""
    if not isinstance(url, str) or len(url) > 8192 or any(ord(c) < 32 for c in url):
        raise ValueError("URL no válida")
    try:
        parsed = urlsplit(url)
        host = parsed.hostname or ""
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Puerto o host no válido") from exc
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("No se permiten direcciones IP")
    if (parsed.scheme != "https" or not host or parsed.username is not None
            or parsed.password is not None or port not in (None, 443)
            or not trusted_host(host, domains)):
        raise ValueError("Solo se permiten URL HTTPS de plataformas autorizadas")
    return url


def mime_extension(mime: str) -> str | None:
    return MEDIA_EXTENSIONS.get(mime.split(";", 1)[0].strip().lower())


def decoded_data_url(url: str, max_bytes: int) -> bytes:
    header, separator, encoded = url.partition(",")
    if not separator or not header.endswith(";base64") or len(encoded) > (max_bytes * 4 // 3 + 8):
        raise ValueError("data URL inválida o demasiado grande")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except binascii.Error as exc:
        raise ValueError("base64 inválido") from exc
    if len(raw) > max_bytes:
        raise ValueError("Recurso demasiado grande")
    return raw


def embedded_bytes(content: dict, max_bytes: int) -> bytes | None:
    value = content.get("text")
    if not isinstance(value, str) or content.get("encoding") != "base64":
        return None
    if len(value) > (max_bytes * 4 // 3 + 8):
        raise ValueError("Contenido HAR demasiado grande")
    try:
        raw = base64.b64decode(value, validate=True)
    except binascii.Error as exc:
        raise ValueError("Contenido HAR base64 incorrecto") from exc
    if len(raw) > max_bytes:
        raise ValueError("Contenido HAR demasiado grande")
    return raw


def save_bytes(destination: Path, chunks, max_bytes: int) -> None:
    """Escribe atómicamente y elimina archivos parciales si falla la descarga."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".media-", delete=False) as handle:
            temporary = Path(handle.name)
            total = 0
            for chunk in chunks:
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError("Descarga superior al límite de tamaño")
                handle.write(chunk)
        os.replace(temporary, destination)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def fetch_media(url: str, destination: Path, expected_mime: str, max_bytes: int) -> None:
    validate_url(url, MEDIA_HOSTS)
    # Sin cookies, cabeceras del HAR, proxies heredados ni redirecciones a terceros.
    with requests.Session() as session:
        session.trust_env = False
        with session.get(url, timeout=(5, 25), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            if response.is_redirect or 300 <= response.status_code < 400:
                raise ValueError("No se siguen redirecciones")
            actual_mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
            if actual_mime != expected_mime or mime_extension(actual_mime) is None:
                raise ValueError("Tipo MIME inesperado")
            size = response.headers.get("Content-Length")
            if size and int(size) > max_bytes:
                raise ValueError("Recurso demasiado grande")
            save_bytes(destination, response.iter_content(chunk_size=65536), max_bytes)


def download_har(har_path: Path, out_dir: Path, max_bytes: int, max_items: int) -> tuple[int, int]:
    if har_path.stat().st_size > MAX_HAR_BYTES:
        raise ValueError("El HAR supera 20 MiB")
    with har_path.open(encoding="utf-8") as handle:
        entries = json.load(handle)["log"]["entries"]
    if not isinstance(entries, list):
        raise ValueError("El HAR no contiene entradas válidas")
    found, downloaded = 0, 0
    seen: set[str] = set()
    for entry in entries:
        if found >= max_items:
            break
        try:
            content = entry["response"]["content"]
            mime = content.get("mimeType", "").split(";", 1)[0].lower().strip()
            extension = mime_extension(mime)
            if extension is None:
                continue
            url = entry["request"]["url"]
            if url in seen:
                continue
            seen.add(url)
            found += 1
            dest = out_dir / "har" / f"recurso_{found:04d}{extension}"
            if dest.exists():
                continue
            embedded = embedded_bytes(content, max_bytes)
            if embedded is not None:
                save_bytes(dest, (embedded,), max_bytes)
            elif isinstance(url, str) and url.startswith("data:"):
                if not url.startswith(f"data:{mime};base64,"):
                    raise ValueError("Tipo de data URL no coincide")
                save_bytes(dest, (decoded_data_url(url, max_bytes),), max_bytes)
            else:
                fetch_media(url, dest, mime, max_bytes)
            downloaded += 1
        except (KeyError, TypeError, ValueError, requests.RequestException, OSError) as exc:
            print(f"Recurso HAR omitido: {type(exc).__name__}", file=sys.stderr)
    return found, downloaded


def select_backends(url: str, preferred: str) -> tuple[str, ...]:
    if preferred != "auto":
        return (preferred,)
    host = urlsplit(url).hostname or ""
    if trusted_host(host, ("youtube.com", "youtu.be", "vimeo.com", "twitch.tv", "soundcloud.com", "dailymotion.com")):
        return ("yt-dlp",)
    return ("gallery-dl", "yt-dlp")


def backend_command(backend: str, url: str, out_dir: Path, max_bytes: int, max_items: int) -> list[str]:
    if backend == "gallery-dl":
        return [sys.executable, "-m", "gallery_dl", "--config-ignore", "--no-input",
                "--restrict-filenames", "windows", "--windows-filenames", "--directory", str(out_dir),
                "--filesize-max", str(max_bytes), "--range", f"1-{max_items}",
                "--http-timeout", "25", "--retries", "2", url]
    if backend == "yt-dlp":
        return [sys.executable, "-m", "yt_dlp", "--ignore-config", "--no-playlist",
                "--no-overwrites", "--restrict-filenames", "--windows-filenames",
                "--paths", str(out_dir), "--output", "%(id)s.%(ext)s",
                "--max-filesize", str(max_bytes), "--max-downloads", str(max_items),
                "--socket-timeout", "25", "--retries", "2", "--fragment-retries", "2", url]
    raise ValueError("Extractor no permitido")


def download_post(url: str, out_dir: Path, backend: str, max_bytes: int, max_items: int) -> int:
    validate_url(url, POST_HOSTS)
    successes = 0
    for selected in select_backends(url, backend):
        dest = out_dir / selected
        dest.mkdir(parents=True, exist_ok=True)
        command = backend_command(selected, url, dest, max_bytes, max_items)
        try:
            completed = subprocess.run(command, shell=False, capture_output=True, text=True, timeout=180, check=False)
        except (OSError, subprocess.TimeoutExpired):
            print(f"{selected}: no disponible o agotó el tiempo", file=sys.stderr)
            continue
        if completed.returncode == 0:
            successes += 1
        else:
            # No imprimir stdout/stderr: podrían contener URL con tokens privados.
            print(f"{selected}: error de descarga ({completed.returncode})", file=sys.stderr)
    return successes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Descarga multimedia desde HAR o publicaciones públicas")
    parser.add_argument("--har", type=Path, help="HAR local (no se envían sus cookies)")
    parser.add_argument("--url", action="append", default=[], help="URL HTTPS de publicación; repetible")
    parser.add_argument("--output", type=Path, default=Path("multimedia_descargada"))
    parser.add_argument("--backend", choices=("auto", "gallery-dl", "yt-dlp"), default="auto")
    parser.add_argument("--max-size-mb", type=int, default=100)
    parser.add_argument("--max-items", type=int, default=DEFAULT_MAX_ITEMS)
    args = parser.parse_args(argv)
    if not args.har and not args.url:
        if Path("captura.har").is_file():
            args.har = Path("captura.har")
        else:
            parser.error("Debes indicar --url o --har")
    if not (1 <= args.max_size_mb <= 1024 and 1 <= args.max_items <= 100):
        parser.error("Límites válidos: 1–1024 MiB y 1–100 recursos")
    max_bytes = args.max_size_mb * 1024 * 1024
    try:
        for url in args.url:
            validate_url(url, POST_HOSTS)
        if args.har:
            found, downloaded = download_har(args.har, args.output, max_bytes, args.max_items)
            print(f"HAR: {downloaded}/{found} recursos descargados")
        failed = 0
        for url in args.url:
            if not download_post(url, args.output, args.backend, max_bytes, args.max_items):
                failed += 1
        return 1 if failed else 0
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())