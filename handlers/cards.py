from pathlib import Path
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import (
    pull_card_from_series,
    add_card_to_user,
    get_card_count_for_user,  # nova função no queries.py
)
from config import CARDS_DIR, DB_FILE
from utils.formatters import formatar_categoria
from utils.image_cache import get_card_image

# -----------------------------------------------------------------------------
# Configuração de categorias e respectivas pastas dentro de assets/
# -----------------------------------------------------------------------------
TIPO_MAP = {
    "cat_series": "series",
    "cat_animes": "animes",
    "cat_jogos": "jogos",
}

# ───────────────────────────── /pull – nível 1 ───────────────────────────────
async def pull_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Envia o gif introdutório com os botões de categoria."""
    gif_path = Path(CARDS_DIR) / "intro" / "intro.gif"
    keyboard = [
        [
            InlineKeyboardButton("🎞️ Séries", callback_data="cat_series"),
            InlineKeyboardButton("🎌 Animes", callback_data="cat_animes"),
            InlineKeyboardButton("🎮 Jogos", callback_data="cat_jogos"),
        ]
    ]
    with gif_path.open("rb") as gif_file:
        await update.message.reply_animation(
            animation=gif_file,
            caption="Escolha a categoria:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

# ─────────────────────────── helpers de listagem/sorteio ─────────────────────

def listar_series_por_tipo(tipo: str) -> list[str]:
    """Retorna nomes de subpastas dentro de assets/<tipo>."""
    base_dir = Path(CARDS_DIR) / tipo
    if not base_dir.exists():
        return []
    return [p.name for p in base_dir.iterdir() if p.is_dir()]


async def enviar_carta(chat, user_id: int, tipo: str, series_name: str):
    """Sorteia uma carta da série, registra no banco, envia ao usuário."""
    # Sorteia carta (ou recupera pelo banco)
    card_id, card_name, image_filename = await pull_card_from_series(
        user_id, series_name
    )
    if card_id is None:
        await chat.reply_text("❌ Série ou figurinhas não encontradas.")
        return

    # Registra ganho da carta
    await add_card_to_user(user_id, card_id)

    # Conta cópias que o usuário tem após adicionar
    qtd = await get_card_count_for_user(user_id, card_id)

    # Monta legenda
    legenda = (
        f"Parabéns, você recebeu #{card_id}: {card_name}!\n"
        f"📦 Você agora possui {qtd} no inventário."
    )

    try:
        image_data = get_card_image(tipo, series_name, image_filename)
        await chat.reply_photo(photo=image_data, caption=legenda)
    except Exception as e:
        print(f"[ERRO] Ao enviar carta: {e}")
        await chat.reply_text("❌ Falha ao processar a imagem.")


# ─────────────────────── único handler de todos os botões ────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # ------------------------ Nível 2: escolha da categoria ------------------
    if data in TIPO_MAP:
        tipo = TIPO_MAP[data]
        context.user_data["tipo_selecionado"] = tipo  # guarda categoria

        series_list = listar_series_por_tipo(tipo)
        if not series_list:
            await query.edit_message_caption(caption="Nenhuma série encontrada.")
            await query.edit_message_reply_markup(reply_markup=None)
            return

        keyboard = [
            [InlineKeyboardButton(formatar_categoria(name), callback_data=f"serie_{name}")]
            for name in series_list
        ]
        await query.edit_message_caption(
            caption="Escolha a série:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # ------------------------ Nível 3: escolha da série ----------------------
    if data.startswith("serie_"):
        series_name = data.split("_", 1)[1]
        tipo = context.user_data.get("tipo_selecionado", "animes")  # default

        await enviar_carta(query.message, user_id, tipo, series_name)

        # Remove a mensagem de seleção
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id,
        )
