# O_01_curl

Este proxecto forma parte da tarefa **O01.01 Libraría request e cURL** de Despregamento de Aplicacións Web.  
O obxectivo é automatizar a descarga de imaxes dunha rede social simulando as peticións que fai o navegador, empregando un ficheiro HAR e a libraría `requests` de Python.

---

## 📄 Enunciado da práctica

Na seguinte tarefa imos intentar automatizar a descarga de imaxes dunha rede social.  
O principal escollo é a autorización: o servidor comproba que a petición da imaxe teña permiso para poder vela (e descargala).  

Para iso, obtemos as **cabeceiras e cookies** dun navegador, e cun script en Python simulamos que é o propio navegador quen fai as peticións, aportando a nosa autorización almacenada nas cookies.

Pasos principais:
1. Exportar un ficheiro HAR cunha sesión iniciada na rede social.
2. Copiar como cURL unha petición de imaxe e convertela a Python con [curlconverter.com](https://curlconverter.com/).
3. Adaptar o código xerado ao script de Python.
4. Ler o HAR, filtrar as imaxes e descargalas con `requests`.

---

## 📌 Estrutura do proxecto
- `o01_01_sambade_saa.py`: Script principal para procesar o ficheiro HAR e descargar as imaxes.
- `auth_config.example.py`: Plantilla pública para a configuración local.
- `auth_config.py`: Configuración local con headers/cookies; nunca se versiona.
- `captura.har` / `captura_sanitizada.har`: Ficheiros HAR exportados desde Firefox (excluídos do repositorio).
- `imaxes_descargadas/`: Directorio onde se gardan as imaxes descargadas polo script.
- `imagenes_listado.txt`: Ficheiro de rexistro con información das imaxes procesadas.
- `.gitignore`: Exclúe ficheiros sensibles e directorios xerados automaticamente.

⚠️ **Nota importante:**  
Os ficheiros HAR están excluídos do repositorio por motivos de seguridade, xa que conteñen cookies e tokens de sesión. Cada usuario debe xerar o seu propio HAR seguindo as instrucións.

---

## 📝 Como xerar o ficheiro HAR en X (antiga Twitter)

Para xerar o ficheiro HAR necesario, segue estes pasos en X (antiga Twitter):

1. Abre unha **ventá privada** en Firefox, sen ningunha extensión activada.
2. Inicia sesión na túa conta de X.
3. Preme F12 para abrir as ferramentas de desenvolvemento e vai á pestana **Rede/Network**.
4. Actualiza a páxina ou navega ata a sección onde aparecen as imaxes que queres descargar.
5. Fai clic dereito en calquera punto da lista de peticións e selecciona **"Exportar como HAR"** ou **"Save all as HAR"**.
6. Garda o ficheiro HAR e cópiao ao directorio do proxecto co nome `captura.har`.

⚠️ **Importante:** Non uses extensións, xa que poden modificar as peticións ou engadir cabeceiras/cookies non desexadas.

### 🔑 Configuración local de cookies e headers

As credenciais non deben copiarse ao script principal nin publicarse no repositorio. Crea `auth_config.py` a partir da plantilla:

```bash
copy auth_config.example.py auth_config.py
```

Despois de xerar o HAR, extrae localmente as cookies de autenticación e configura os headers apropiados en `auth_config.py`:

1. Abre o ficheiro HAR e busca unha petición de imaxe exitosa.
2. Copia as cookies e headers usando [curlconverter.com](https://curlconverter.com/).
3. Actualiza `auth_config.py` coas túas cookies e headers específicos. Este ficheiro está no `.gitignore`; comproba sempre `git status` antes de facer push.

Se as cookies expostas neste proxecto foron reais, pecha a sesión correspondente e revógaas/renóvaas en X. Unha credencial publicada debe considerarse comprometida aínda que despois se elimine do código actual.

---

## 🔧 Requisitos
- Python 3
- Paquete `requests`

Instalación de dependencias:
```bash
pip install requests
```

## Uso
1. Exporta un ficheiro HAR desde Firefox e cópiao como `captura.har` no directorio do proxecto.
2. Executa o script:
   ```bash
   python o01_01_sambade_saa.py
   ```
3. As imaxes detectadas gardaranse en `imaxes_descargadas/`.

## Funcionamento
O script:
- Lê o ficheiro HAR especificado (`captura.har` por defecto).
- Busca todas as entradas de resposta con tipo MIME de imaxe.
- Descarga cada imaxe usando cookies de autenticación para evitar erros 403.
- Garda as imaxes en `imaxes_descargadas/` con nomes secuenciais.
- Xera un ficheiro de rexistro `imagenes_listado.txt` con información detallada de cada descarga.

### 📊 Resultados típicos
- **Imaxes públicas** (favicons, emojis): Descargan correctamente (200 OK)
- **Imaxes de perfil/contido**: Requiren autenticación, poden dar erro 403 sen cookies válidas
- **Imaxes base64**: Procésanse directamente sen petición HTTP

## Autoría
- Desenvolvido por Rodrigo Sambade

## Licenza
Uso educativo.
