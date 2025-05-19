# utils/image_cache.py
from functools import lru_cache
from pathlib import Path
from config import CARDS_DIR
from PIL import Image
from io import BytesIO
from config import IMAGE_QUALITY
import os



@lru_cache(maxsize=100)  # Cache para 100 imagens
def load_image(image_path: str) -> bytes:
    """Carrega a imagem em memória com cache"""
    with open(image_path, 'rb') as f:
        return f.read()
    
@lru_cache(maxsize=100)
def load_optimized_image(image_path: str) -> BytesIO:
    """Otimiza imagens convertendo para JPG"""
    with Image.open(image_path) as img:
        # Converte para RGB (necessário para JPG)
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        # Redimensiona se necessário (opcional)
        if max(img.size) > 1024:
            img.thumbnail((1024, 1024))
            
        buffer = BytesIO()
        # Altere para JPEG e ajuste a qualidade
        img.save(buffer, format='JPEG', quality=IMAGE_QUALITY)
        buffer.seek(0)
        return buffer  

def get_card_image(tipo: str, series: str, filename: str) -> bytes:
    # tipo pode ser: "animes", "series", "jogos"
    path = Path(CARDS_DIR) / tipo / series / filename
    with path.open("rb") as f:
        return f.read()

