import os
import json
import requests
import mimetypes
import base64

# -------------------------------
# Función para gardar unha imaxe
# -------------------------------
def gardar_imaxe(directorio, nome_imaxe, contido):
    os.makedirs(directorio, exist_ok=True)
    ruta_completa = os.path.join(directorio, nome_imaxe)
    with open(ruta_completa, "wb") as f:
        f.write(contido)
    print(f"Imaxe gardada en: {ruta_completa}")


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

    # 3. Headers e cookies para autenticación en X/Twitter
    cookies = {
        'guest_id': 'REDACTED_SESSION_VALUE',
        '__cf_bm': 'REDACTED_SESSION_VALUE',
        'gt': 'REDACTED_SESSION_VALUE',
        '__cuid': 'REDACTED_SESSION_VALUE',
        'kdt': 'REDACTED_SESSION_VALUE',
        'twid': 'REDACTED_SESSION_VALUE',
        'ct0': 'REDACTED_SESSION_VALUE',
        'auth_token': 'REDACTED_SESSION_VALUE',
        'lang': 'es',
        'd_prefs': 'REDACTED_SESSION_VALUE',
        'guest_id_ads': 'REDACTED_SESSION_VALUE',
        'guest_id_marketing': 'REDACTED_SESSION_VALUE',
        'personalization_id': 'REDACTED_SESSION_VALUE',
    }

    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:139.0) Gecko/20100101 Firefox/139.0',
        'Accept': 'image/avif,image/webp,image/png,image/svg+xml,image/*;q=0.8,*/*;q=0.5',
        'Accept-Language': 'gl-ES,gl;q=0.8,en-US;q=0.5,en;q=0.3',
        'Referer': 'https://x.com/',
        'DNT': '1',
        'Sec-GPC': '1',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
        'Priority': 'u=5, i',
    }

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
                resposta = requests.get(url, headers=headers, cookies=cookies)
                if resposta.status_code == 200:
                    gardar_imaxe(directorio_saida, nome, resposta.content)
                else:
                    print(f"Erro {resposta.status_code} ao descargar {url}")
        except Exception as e:
            print(f"Erro con {url}: {e}")


if __name__ == "__main__":
    main()
