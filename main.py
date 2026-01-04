from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, HttpUrl
import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
import cssutils
import logging
from fontTools import ttLib
import io
import base64

# Desabilitar logs do cssutils
cssutils.log.setLevel(logging.CRITICAL)

app = FastAPI(
    title="Font Extractor API - Serverless",
    description="Extract and convert fonts without server-side storage",
    version="2.0.0"
)

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
    font_data: str  # Base64 encoded font
    source_format: str
    target_format: str
    font_name: str

# Formatos suportados
SUPPORTED_FORMATS = {
    'ttf': 'TrueType Font',
    'otf': 'OpenType Font',
    'woff': 'Web Open Font Format',
    'woff2': 'Web Open Font Format 2',
    'eot': 'Embedded OpenType',
    'svg': 'SVG Font'
}

def detect_font_format(url: str) -> str:
    """Detecta o formato da fonte pela URL"""
    url_lower = url.lower()
    if '.woff2' in url_lower or 'woff2' in url_lower:
        return 'woff2'
    elif '.woff' in url_lower or 'woff' in url_lower:
        return 'woff'
    elif '.ttf' in url_lower:
        return 'ttf'
    elif '.otf' in url_lower:
        return 'otf'
    elif '.eot' in url_lower:
        return 'eot'
    elif '.svg' in url_lower:
        return 'svg'
    return 'unknown'

def extract_fonts_from_css(css_content: str, base_url: str) -> list:
    """Extrai URLs de fontes de conteúdo CSS"""
    fonts = []
    
    try:
        sheet = cssutils.parseString(css_content)
        for rule in sheet:
            if rule.type == rule.FONT_FACE_RULE:
                font_family = None
                src_value = None
                
                for prop in rule.style:
                    if prop.name == 'font-family':
                        font_family = prop.value.strip('\'"')
                    elif prop.name == 'src':
                        src_value = prop.value
                
                if src_value:
                    # Extrair URLs
                    urls = re.findall(r'url\([\'"]?([^\'"()]+)[\'"]?\)', src_value)
                    for url in urls:
                        # Ignorar data URIs
                        if url.startswith('data:'):
                            continue
                            
                        full_url = urljoin(base_url, url)
                        font_format = detect_font_format(full_url)
                        
                        fonts.append({
                            'name': font_family or 'Unknown',
                            'url': full_url,
                            'format': font_format
                        })
    except Exception as e:
        print(f"Erro ao parsear CSS: {e}")
    
    return fonts

@app.get("/")
async def root():
    return {
        "message": "Font Extractor API - Serverless Mode",
        "version": "2.0.0",
        "storage": "client-side only",
        "endpoints": {
            "POST /extract-fonts": "Extract font URLs from website",
            "POST /convert-font": "Convert font between formats",
            "GET /proxy-font": "Proxy font download (CORS bypass)",
            "GET /supported-formats": "List supported formats",
            "GET /docs": "Interactive API documentation"
        }
    }

@app.post("/extract-fonts")
async def extract_fonts(request: URLRequest):
    """
    Extrai apenas as URLs das fontes, sem baixar.
    O cliente baixa diretamente.
    """
    try:
        url = str(request.url)
        
        # Buscar HTML
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        fonts = []
        seen_urls = set()
        
        # 1. CSS inline
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                fonts.extend(extract_fonts_from_css(style_tag.string, url))
        
        # 2. CSS externo
        for link in soup.find_all('link', rel='stylesheet'):
            css_url = urljoin(url, link.get('href', ''))
            try:
                css_response = requests.get(css_url, headers=headers, timeout=5)
                fonts.extend(extract_fonts_from_css(css_response.text, css_url))
            except:
                pass
        
        # 3. @import rules
        css_import_pattern = r'@import\s+[\'"]([^\'"]+)[\'"]'
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                imports = re.findall(css_import_pattern, style_tag.string)
                for import_url in imports:
                    import_url = urljoin(url, import_url)
                    try:
                        css_response = requests.get(import_url, headers=headers, timeout=5)
                        fonts.extend(extract_fonts_from_css(css_response.text, import_url))
                    except:
                        pass
        
        # 4. Remover duplicatas
        unique_fonts = []
        for font in fonts:
            if font['url'] not in seen_urls:
                seen_urls.add(font['url'])
                unique_fonts.append(font)
        
        return {
            "success": True,
            "url": url,
            "fonts_found": len(unique_fonts),
            "fonts": unique_fonts,
            "message": "Fonts extracted. Download on client-side."
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/convert-font")
async def convert_font(request: ConvertFontRequest):
    """
    Converte fonte recebida em base64 para outro formato.
    Retorna fonte convertida em base64 (sem salvar no servidor).
    """
    try:
        # Decodificar base64
        font_bytes = base64.b64decode(request.font_data)
        
        # Criar buffer de entrada
        input_buffer = io.BytesIO(font_bytes)
        
        # Carregar fonte
        font = ttLib.TTFont(input_buffer)
        
        # Buffer de saída
        output_buffer = io.BytesIO()
        
        # Configurar flavor baseado no formato
        if request.target_format == 'woff':
            font.flavor = 'woff'
        elif request.target_format == 'woff2':
            font.flavor = 'woff2'
        else:
            font.flavor = None
        
        # Salvar no buffer
        font.save(output_buffer)
        font.close()
        
        # Converter para base64
        output_buffer.seek(0)
        converted_base64 = base64.b64encode(output_buffer.read()).decode('utf-8')
        
        return {
            "success": True,
            "font_name": request.font_name,
            "source_format": request.source_format,
            "target_format": request.target_format,
            "font_data": converted_base64,
            "message": "Font converted successfully"
        }
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Conversion error: {str(e)}")

@app.get("/supported-formats")
async def supported_formats():
    """Lista formatos suportados"""
    return {
        "formats": list(SUPPORTED_FORMATS.keys()),
        "details": SUPPORTED_FORMATS
    }

@app.get("/proxy-font")
async def proxy_font(url: str):
    """
    Proxy para baixar fontes que bloqueiam CORS.
    Retorna a fonte como stream.
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10, stream=True)
        response.raise_for_status()
        
        # Detectar content-type
        content_type = response.headers.get('content-type', 'application/octet-stream')
        
        return StreamingResponse(
            response.iter_content(chunk_size=8192),
            media_type=content_type
        )
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Proxy error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms"""
    return {"status": "healthy", "version": "2.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
