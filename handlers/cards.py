import os
import random
import aiosqlite
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.queries import pull_card_from_series, add_card_to_user
from config import CARDS_DIR, DB_FILE
from utils.formatters import formatar_categoria
from utils.image_cache import get_card_image

# ───────────────────────────── /pull – nível 1 ───────────────────────────────
async def pull_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif_path = os.path.join(CARDS_DIR, "intro", "intro.gif")
    keyboard = [
        [
            InlineKeyboardButton("🎞️ Séries", callback_data="cat_series"),
            InlineKeyboardButton("🎌 Animes",  callback_data="cat_animes"),
        ]
    ]
    # envia mensagem com gif e botões
    with open(gif_path, "rb") as gif_file:
        await update.message.reply_animation(
            animation=gif_file,
            caption="Escolha a categoria:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ─────────── auxiliar: lista as séries da categoria (nível 2) ────────────────
async def enviar_lista_series(chat, tipo: str):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT name FROM series ORDER BY name LIMIT 10"
            # futuro: WHERE tipo=? , (tipo,)
        )
        series_list = await cursor.fetchall()

    if not series_list:
        await chat.reply_text("Nenhuma série cadastrada nessa categoria.")
        return

    keyboard = [
        [InlineKeyboardButton(formatar_categoria(s[0]), callback_data=f"serie_{s[0]}")]
        for s in series_list
    ]
    await chat.reply_text(
        "Escolha a série:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─────────── auxiliar: sorteia, registra e envia a carta (nível final) ───────
async def enviar_carta(chat, user_id: int, series_name: str):
    card_id, card_name, image_filename = await pull_card_from_series(user_id, series_name)
    if card_id is None:
        await chat.reply_text("❌ Série ou figurinhas não encontradas.")
        return

    try:
        # Substitua o bloco de abertura de arquivo por:
        image_data = get_card_image(series_name, image_filename)
        await chat.reply_photo(
            photo=image_data,
            caption=f"🎉 Nova carta: {card_name}!"
        )
        await add_card_to_user(user_id, card_id)
    except Exception as e:
        print(f"[ERRO] Ao enviar carta: {e}")
        await chat.reply_text("❌ Falha ao processar a imagem.")



# ─────────────────────── único handler de todos os botões ────────────────────
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data in ("cat_series", "cat_animes"):
        tipo = "series" if data == "cat_series" else "animes"

        # busca séries no banco (exemplo simplificado)
        async with aiosqlite.connect(DB_FILE) as db:
            cursor = await db.execute(
                "SELECT name FROM series ORDER BY name LIMIT 10"
                # futuramente filtrar por tipo
            )
            series_list = await cursor.fetchall()

        if not series_list:
            await query.edit_message_caption(caption="Nenhuma série encontrada.")
            await query.edit_message_reply_markup(reply_markup=None)
            return

        keyboard = [
            [InlineKeyboardButton(formatar_categoria(s[0]), callback_data=f"serie_{s[0]}")]
            for s in series_list
        ]
        # mantém a animação, só atualiza o texto e botões
        await query.edit_message_caption(
            caption="Escolha a série:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data.startswith("serie_"):
        series_name = data.split("_", 1)[1]
        await enviar_carta(query.message, user_id, series_name)

        # apaga a mensagem com o gif e botões após enviar a carta
        await context.bot.delete_message(
            chat_id=query.message.chat_id,
            message_id=query.message.message_id
        )
