import os
import json
import requests
import mimetypes
import base64
from urllib.parse import urlparse

try:
    from auth_config import HEADERS, COOKIES
except ImportError as exc:
    raise SystemExit(
        "Falta auth_config.py. Crea una copia de auth_config.example.py "
        "y añade tus credenciales localmente; ese archivo está excluido de Git."
    ) from exc

# -------------------------------
# Función para gardar unha imaxe
# -------------------------------
def gardar_imaxe(directorio, nome_imaxe, contido):
    os.makedirs(directorio, exist_ok=True)
    ruta_completa = os.path.join(directorio, nome_imaxe)
    with open(ruta_completa, "wb") as f:
        f.write(contido)
    print(f"Imaxe gardada en: {ruta_completa}")


def e_host_autorizado(url):
    """Evita enviar credenciais a dominios de terceiros incluidos no HAR."""
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return any(host == dominio or host.endswith(f".{dominio}") for dominio in (
        "x.com",
        "twitter.com",
        "twimg.com",
    ))


def main():
    # Nome do ficheiro HAR exportado desde Firefox
    ficheiro_har = "captura.har"
    directorio_saida = "imaxes_descargadas"

    # 1. Ler o ficheiro HAR
    with open(ficheiro_har, "r", encoding="utf-8") as f:
        datos = json.load(f)

    # 2. Filtrar todas as entradas que teñan unha resposta cun tipo MIME de imaxe
    entradas = datos["log"]["entries"]
    urls_imaxes = []
    for entrada in entradas:
        resposta = entrada.get("response", {})
        tipo_mime = resposta.get("content", {}).get("mimeType", "")
        if tipo_mime.startswith("image/"):
            url = entrada["request"]["url"]
            urls_imaxes.append((url, tipo_mime))

    print(f"Detectadas {len(urls_imaxes)} imaxes no HAR.")

    # 4. Descargar e gardar imaxes
    for i, (url, mime) in enumerate(urls_imaxes, start=1):
        try:
            # Extensión segundo MIME
            extension = mimetypes.guess_extension(mime.split(";")[0]) or ".jpg"
            nome = f"imaxe_{i}{extension}"

            if url.startswith("data:image/"):  # caso base64
                header, b64data = url.split(",", 1)
                contido = base64.b64decode(b64data)
                gardar_imaxe(directorio_saida, nome, contido)
            else:  # descarga por HTTP
                credenciais_permitidas = e_host_autorizado(url)
                headers = HEADERS if credenciais_permitidas else {}
                cookies = COOKIES if credenciais_permitidas else {}
                resposta = requests.get(url, headers=headers, cookies=cookies, timeout=30)
                if resposta.status_code == 200:
                    gardar_imaxe(directorio_saida, nome, resposta.content)
                else:
                    print(f"Erro {resposta.status_code} ao descargar {url}")
        except Exception as e:
            print(f"Erro con {url}: {e}")


if __name__ == "__main__":
    main()
