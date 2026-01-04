from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
import re
import os
import hashlib
from urllib.parse import urljoin, urlparse
from pathlib import Path
import cssutils
import logging
from fontTools import ttLib
from fontTools.ttLib import woff2
import tempfile
import shutil

# Desabilitar logs do cssutils
cssutils.log.setLevel(logging.CRITICAL)

app = FastAPI(title="Font Downloader API", description="API para baixar todas as fontes de um site")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLRequest(BaseModel):
    url: HttpUrl

class ConvertFontRequest(BaseModel):
    filename: str
    target_format: str

class FontInfo(BaseModel):
    name: str
    format: str
    url: str
    local_path: str

# Criar pasta para armazenar fontes
FONTS_DIR = Path("downloaded_fonts")
FONTS_DIR.mkdir(exist_ok=True)

CONVERTED_FONTS_DIR = Path("converted_fonts")
CONVERTED_FONTS_DIR.mkdir(exist_ok=True)

# Formatos suportados para conversão
SUPPORTED_FORMATS = {
    'ttf': 'TrueType Font',
    'otf': 'OpenType Font',
    'woff': 'Web Open Font Format',
    'woff2': 'Web Open Font Format 2',
    'eot': 'Embedded OpenType',
    'svg': 'SVG Font'
}

def convert_font(input_path: str, output_format: str) -> str:
    """Converte uma fonte para outro formato usando fonttools"""
    try:
        input_path = Path(input_path)
        
        # Criar nome do arquivo de saída
        output_filename = input_path.stem + f'.{output_format}'
        output_path = CONVERTED_FONTS_DIR / output_filename
        
        # Carregar a fonte
        font = ttLib.TTFont(str(input_path))
        
        # Configurar flavor baseado no formato de saída
        if output_format == 'woff':
            font.flavor = 'woff'
        elif output_format == 'woff2':
            font.flavor = 'woff2'
        else:
            font.flavor = None
        
        # Salvar no novo formato
        font.save(str(output_path))
        font.close()
        
        return str(output_path)
    
    except Exception as e:
        raise Exception(f"Erro ao converter fonte: {str(e)}")

def extract_fonts_from_css(css_content: str, base_url: str) -> list:
    """Extrai URLs de fontes de conteúdo CSS"""
    fonts = []
    
    try:
        sheet = cssutils.parseString(css_content)
        
        for rule in sheet:
            if rule.type == rule.FONT_FACE_RULE:
                font_family = None
                font_urls = []
                
                for prop in rule.style:
                    if prop.name == 'font-family':
                        font_family = prop.value.strip('\'"')
                    elif prop.name == 'src':
                        # Extrair URLs do src
                        url_pattern = r'url\([\'"]?([^\'")]+)[\'"]?\)'
                        matches = re.findall(url_pattern, prop.value)
                        for match in matches:
                            full_url = urljoin(base_url, match)
                            
                            # Detectar formato
                            format_match = re.search(r'format\([\'"]?([^\'")]+)[\'"]?\)', prop.value)
                            font_format = format_match.group(1) if format_match else 'unknown'
                            
                            # Extrair extensão da URL
                            parsed = urlparse(full_url)
                            path_parts = parsed.path.split('.')
                            if len(path_parts) > 1:
                                ext = path_parts[-1].split('?')[0]
                            else:
                                ext = font_format
                            
                            font_urls.append({
                                'url': full_url,
                                'format': font_format,
                                'extension': ext
                            })
                
                if font_family and font_urls:
                    for font_url in font_urls:
                        fonts.append({
                            'family': font_family,
                            'url': font_url['url'],
                            'format': font_url['format'],
                            'extension': font_url['extension']
                        })
    except Exception as e:
        print(f"Erro ao processar CSS: {e}")
    
    return fonts

def download_font(url: str, font_family: str, extension: str) -> str:
    """Baixa uma fonte e salva localmente"""
    try:
        response = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        response.raise_for_status()
        
        # Criar nome de arquivo único
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        safe_family = re.sub(r'[^\w\s-]', '', font_family).strip().replace(' ', '_')
        filename = f"{safe_family}_{url_hash}.{extension}"
        filepath = FONTS_DIR / filename
        
        # Salvar arquivo
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        return str(filepath)
    except Exception as e:
        print(f"Erro ao baixar fonte {url}: {e}")
        return None

@app.get("/")
def read_root():
    return {
        "message": "Font Downloader API",
        "endpoints": {
            "/download-fonts": "POST - Baixa todas as fontes de um site",
            "/list-fonts": "GET - Lista fontes baixadas",
            "/convert-font": "POST - Converte uma fonte para outro formato",
            "/supported-formats": "GET - Lista formatos suportados para conversão",
            "/docs": "GET - Documentação interativa"
        }
    }

@app.post("/download-fonts")
def download_fonts(request: URLRequest):
    """Baixa todas as fontes de um site"""
    url = str(request.url)
    all_fonts = []
    downloaded_fonts = []
    
    try:
        # Fazer requisição para obter HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Processar CSS inline (tags <style>)
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                fonts = extract_fonts_from_css(style_tag.string, url)
                all_fonts.extend(fonts)
        
        # 2. Processar arquivos CSS externos
        for link in soup.find_all('link', rel='stylesheet'):
            css_url = link.get('href')
            if css_url:
                css_url = urljoin(url, css_url)
                try:
                    css_response = requests.get(css_url, headers=headers, timeout=30)
                    css_response.raise_for_status()
                    fonts = extract_fonts_from_css(css_response.text, css_url)
                    all_fonts.extend(fonts)
                except Exception as e:
                    print(f"Erro ao processar CSS externo {css_url}: {e}")
        
        # 3. Processar imports de CSS (@import)
        css_import_pattern = r'@import\s+[\'"]([^\'"]+)[\'"]'
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                imports = re.findall(css_import_pattern, style_tag.string)
                for import_url in imports:
                    import_url = urljoin(url, import_url)
                    try:
                        css_response = requests.get(import_url, headers=headers, timeout=30)
                        css_response.raise_for_status()
                        fonts = extract_fonts_from_css(css_response.text, import_url)
                        all_fonts.extend(fonts)
                    except Exception as e:
                        print(f"Erro ao processar import CSS {import_url}: {e}")
        
        # Remover duplicatas
        unique_fonts = {}
        for font in all_fonts:
            key = font['url']
            if key not in unique_fonts:
                unique_fonts[key] = font
        
        # Baixar cada fonte
        for font in unique_fonts.values():
            local_path = download_font(font['url'], font['family'], font['extension'])
            if local_path:
                downloaded_fonts.append({
                    'name': font['family'],
                    'format': font['format'],
                    'url': font['url'],
                    'local_path': local_path
                })
        
        return {
            'success': True,
            'url': url,
            'fonts_found': len(unique_fonts),
            'fonts_downloaded': len(downloaded_fonts),
            'fonts': downloaded_fonts
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Erro ao acessar URL: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao processar site: {str(e)}")

@app.get("/list-fonts")
def list_fonts():
    """Lista todas as fontes baixadas"""
    if not FONTS_DIR.exists():
        return {"fonts": []}
    
    fonts = []
    for font_file in FONTS_DIR.iterdir():
        if font_file.is_file():
            fonts.append({
                'filename': font_file.name,
                'size': font_file.stat().st_size,
                'path': str(font_file)
            })
    
    return {
        'total': len(fonts),
        'fonts': fonts
    }

@app.get("/download-file/{filename}")
def download_file(filename: str):
    """Baixa um arquivo de fonte específico"""
    filepath = FONTS_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/supported-formats")
def get_supported_formats():
    """Lista todos os formatos suportados para conversão"""
    return {
        "formats": SUPPORTED_FORMATS,
        "total": len(SUPPORTED_FORMATS)
    }

@app.post("/convert-font")
def convert_font_endpoint(request: ConvertFontRequest):
    """Converte uma fonte para outro formato"""
    filename = request.filename
    target_format = request.target_format.lower()
    
    # Validar formato
    if target_format not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato não suportado. Formatos disponíveis: {', '.join(SUPPORTED_FORMATS.keys())}"
        )
    
    # Verificar se arquivo existe
    input_path = FONTS_DIR / filename
    if not input_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo de fonte não encontrado")
    
    try:
        # Converter fonte
        output_path = convert_font(str(input_path), target_format)
        output_filename = Path(output_path).name
        
        return {
            "success": True,
            "original_file": filename,
            "converted_file": output_filename,
            "format": target_format,
            "download_url": f"/download-converted/{output_filename}"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/download-converted/{filename}")
def download_converted_file(filename: str):
    """Baixa um arquivo de fonte convertido"""
    filepath = CONVERTED_FONTS_DIR / filename
    
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Arquivo convertido não encontrado")
    
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type='application/octet-stream'
    )

@app.get("/list-converted-fonts")
def list_converted_fonts():
    """Lista todas as fontes convertidas"""
    if not CONVERTED_FONTS_DIR.exists():
        return {"fonts": []}
    
    fonts = []
    for font_file in CONVERTED_FONTS_DIR.iterdir():
        if font_file.is_file():
            fonts.append({
                'filename': font_file.name,
                'size': font_file.stat().st_size,
                'path': str(font_file)
            })
    
    return {
        'total': len(fonts),
        'fonts': fonts
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
