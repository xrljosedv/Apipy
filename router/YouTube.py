import requests
from bs4 import BeautifulSoup
import json
import time
import re
from urllib.parse import urlparse, parse_qs, quote

# ============================================================
# SCRAPER PARA Y2MATE (funciona realmente)
# ============================================================

def scrape_y2mate(video_url, format_preference=None):
    """
    Obtiene enlaces de descarga de y2mate.com
    """
    if not video_url:
        return {"status": False, "error": "URL de YouTube requerida"}

    video_id = extract_youtube_id(video_url)
    if not video_id:
        return {"status": False, "error": "URL de YouTube inválida"}

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Origin': 'https://y2mate.nu',
        'Referer': 'https://y2mate.nu/'
    })

    try:
        # 1. Obtener página de análisis
        analyze_url = "https://y2mate.nu/api/convert"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
        }
        data = {
            'v': f'https://www.youtube.com/watch?v={video_id}',
            'f': 'mp3' if format_preference == 'mp3' else 'mp4'
        }
        
        resp = session.post(analyze_url, data=data, headers=headers, timeout=20)
        if resp.status_code != 200:
            return {"status": False, "error": f"Error del servidor: {resp.status_code}"}
        
        json_data = resp.json()
        if json_data.get('status') != 'success':
            return {"status": False, "error": json_data.get('mess', 'Error desconocido')}

        # 2. Extraer información
        title = json_data.get('title', f'YouTube Video {video_id}')
        vid = json_data.get('vid')
        
        formats = []
        # Obtener enlaces de descarga
        links = json_data.get('links', {})
        
        if 'mp3' in links:
            for quality, info in links['mp3'].items():
                formats.append({
                    'type': 'mp3',
                    'quality': quality,
                    'url': info.get('k'),
                    'size': info.get('size', '')
                })
        if 'mp4' in links:
            for quality, info in links['mp4'].items():
                formats.append({
                    'type': 'mp4',
                    'quality': quality,
                    'url': info.get('k'),
                    'size': info.get('size', '')
                })
        
        # Filtrar si se especificó
        if format_preference:
            formats = [f for f in formats if f['type'] == format_preference]

        return {
            "status": bool(formats),
            "video_id": video_id,
            "title": title,
            "formats": formats,
            "error": None if formats else "No se encontraron enlaces para el formato solicitado"
        }

    except requests.exceptions.RequestException as e:
        return {"status": False, "error": f"Error de conexión: {str(e)}"}
    except json.JSONDecodeError:
        return {"status": False, "error": "Respuesta inválida del servidor (no JSON)"}
    except Exception as e:
        return {"status": False, "error": f"Error procesando datos: {str(e)}"}


def extract_youtube_id(url):
    patterns = [
        r'(?:v=|\/)([0-9A-Za-z_-]{11})(?:[?&]|$)',
        r'youtu\.be\/([0-9A-Za-z_-]{11})',
        r'embed\/([0-9A-Za-z_-]{11})'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


# ============================================================
# DESCARGA PROXY (descarga el archivo desde el servidor de la API)
# ============================================================

def proxy_download(url, format_type='mp3'):
    """
    Descarga el archivo desde el enlace temporal y lo retorna como streaming.
    Para usar en un endpoint que devuelva directamente el archivo.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Referer': 'https://y2mate.nu/'
    }
    
    try:
        resp = requests.get(url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()
        
        # Determinar nombre de archivo
        content_disposition = resp.headers.get('Content-Disposition', '')
        filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', content_disposition)
        if filename_match:
            filename = filename_match.group(1).strip('"\'')
        else:
            # Extraer de la URL o usar genérico
            filename = url.split('/')[-1].split('?')[0]
            if not filename:
                filename = f'download.{format_type}'
        
        # Retornar contenido binario y headers para servir como descarga
        return {
            'status': True,
            'filename': filename,
            'content_type': resp.headers.get('Content-Type', 'application/octet-stream'),
            'content': resp.content,  # o usar iter_content para streaming
            'size': len(resp.content)
        }
    except Exception as e:
        return {'status': False, 'error': str(e)}


# ============================================================
# ENDPOINTS DE API
# ============================================================

def run_links(ctx):
    """Endpoint para obtener enlaces de descarga."""
    req = ctx['req']
    query_params = req.get('query', {})
    
    video_url = query_params.get('url') or query_params.get('q') or query_params.get('v')
    if not video_url:
        return {
            'status': False,
            'error': 'Parámetro requerido',
            'message': "Debes proporcionar 'url' con el enlace de YouTube",
            'code': 400
        }
    
    format_pref = query_params.get('format', '').lower()
    
    start_time = time.time()
    data = scrape_y2mate(video_url, format_pref)
    data['tiempo_respuesta'] = f"{time.time() - start_time:.2f}s"
    
    return data


def run_download(ctx):
    """
    Endpoint para descargar directamente el archivo desde el servidor de la API.
    Recibe 'url' del video y opcional 'format' y 'quality'.
    """
    req = ctx['req']
    query_params = req.get('query', {})
    
    video_url = query_params.get('url')
    if not video_url:
        return {
            'status': False,
            'error': 'Parámetro requerido: url',
            'code': 400
        }
    
    format_pref = query_params.get('format', 'mp3').lower()
    quality = query_params.get('quality')  # opcional
    
    # 1. Obtener enlaces
    links_data = scrape_y2mate(video_url, format_pref)
    if not links_data['status']:
        return links_data  # retornar error
    
    formats = links_data['formats']
    
    # 2. Seleccionar el enlace adecuado (mejor calidad por defecto)
    if quality:
        selected = next((f for f in formats if f['quality'] == quality), None)
        if not selected:
            return {'status': False, 'error': f'Calidad {quality} no disponible'}
    else:
        # Ordenar por calidad (mayor kbps o p)
        if format_pref == 'mp3':
            formats.sort(key=lambda x: int(re.search(r'(\d+)', x['quality']).group(1)), reverse=True)
        else:
            formats.sort(key=lambda x: int(re.search(r'(\d+)', x['quality']).group(1)), reverse=True)
        selected = formats[0] if formats else None
    
    if not selected:
        return {'status': False, 'error': 'No hay enlaces disponibles'}
    
    # 3. Descargar archivo a través del proxy
    download_result = proxy_download(selected['url'], format_pref)
    if not download_result['status']:
        return {'status': False, 'error': download_result['error']}
    
    # 4. Devolver como respuesta de archivo (esto depende del framework de la API)
    # Asumiendo que la función puede devolver headers personalizados y el contenido binario.
    return {
        'status': True,
        'filename': download_result['filename'],
        'content_type': download_result['content_type'],
        'data': download_result['content'],  # bytes
        'size': download_result['size'],
        'video_title': links_data['title']
    }


# ============================================================
# CONFIGURACIÓN DE ENDPOINTS
# ============================================================

endpoints = [
    {
        'metode': 'GET',
        'endpoint': '/ytmp3/links',
        'name': 'YouTube to MP3/MP4 - Obtener Enlaces',
        'category': 'Downloader',
        'description': 'Obtiene enlaces de descarga MP3/MP4 de YouTube usando servicio real',
        'tags': ['YouTube', 'MP3', 'MP4', 'Downloader'],
        'example': '?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=mp3',
        'parameters': [
            {'name': 'url', 'in': 'query', 'required': True, 'schema': {'type': 'string'}, 'description': 'URL del video de YouTube', 'example': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'},
            {'name': 'format', 'in': 'query', 'required': False, 'schema': {'type': 'string', 'enum': ['mp3', 'mp4']}, 'description': 'Filtrar por formato', 'example': 'mp3'}
        ],
        'isPremium': False,
        'isMaintenance': False,
        'isPublic': True,
        'middleware': ['apiKey'],
        'run': run_links
    },
    {
        'metode': 'GET',
        'endpoint': '/ytmp3/download',
        'name': 'YouTube to MP3/MP4 - Descargar Archivo',
        'category': 'Downloader',
        'description': 'Descarga directamente el archivo MP3/MP4 desde el servidor de la API (proxy)',
        'tags': ['YouTube', 'MP3', 'MP4', 'Downloader', 'Proxy'],
        'example': '?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=mp3',
        'parameters': [
            {'name': 'url', 'in': 'query', 'required': True, 'schema': {'type': 'string'}, 'description': 'URL del video de YouTube'},
            {'name': 'format', 'in': 'query', 'required': False, 'schema': {'type': 'string', 'enum': ['mp3', 'mp4']}, 'description': 'Formato deseado (default mp3)', 'example': 'mp3'},
            {'name': 'quality', 'in': 'query', 'required': False, 'schema': {'type': 'string'}, 'description': 'Calidad específica (ej. 320kbps, 720p)', 'example': '320kbps'}
        ],
        'isPremium': False,
        'isMaintenance': False,
        'isPublic': True,
        'middleware': ['apiKey'],
        'run': run_download
    }
]
