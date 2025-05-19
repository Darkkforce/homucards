# utils/inventory_helpers.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import ITEMS_PER_PAGE

def formatar_inventario_texto(cartas, page, total):
    linhas = []
    for card_id, card_name, qty in cartas:
        linhas.append(f"#{card_id} - {card_name} (x{qty})")

    texto = "\n".join(linhas)
    texto += f"\n\nPágina {page + 1} de {(total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE}"
    return texto

def montar_teclado_paginacao(page, total):
    max_page = (total - 1) // ITEMS_PER_PAGE
    buttons = []

    if page > 0:
        buttons.append(InlineKeyboardButton("⬅️ Voltar", callback_data=f"inv_prev_{page}"))
    if page < max_page:
        buttons.append(InlineKeyboardButton("➡️ Avançar", callback_data=f"inv_next_{page}"))

    if buttons:
        return InlineKeyboardMarkup([buttons])
    return None
