from pathlib import Path
from telegram.helpers import escape_markdown

def escape_text(text: str) -> str:
    """Escapa caracteres especiais para MarkdownV2"""
    return escape_markdown(text, version=2)

def formatar_categoria(nome: str) -> str:
    """Formata nomes de categorias"""
    return nome.replace("_", " ").title()

def formatar_card(filename: str) -> str:
    """Formata nomes de arquivos de cartas"""
    nome = Path(filename).stem
    return nome.replace("_", " ").title()



def formatar_categoria(nome: str) -> str:
    return nome.replace("_", " ").title()

def formatar_card(filename: str) -> str:
    return Path(filename).stem.replace("_", " ").title()