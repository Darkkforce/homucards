from telegram import Update
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes
from database.queries import add_user
import re
import aiosqlite
from config import DB_FILE, WELCOME_MESSAGE
from utils.formatters import escape_text
from database.queries import get_user_inventory
from database.queries import add_user
from config import ITEMS_PER_PAGE
from utils.inventory_helpers import formatar_inventario_texto, montar_teclado_paginacao



# ---------- HANDLERS DO BOT ---------- #
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)


async def username_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("❌ Use: /username <seu_nome>")
        return

    username = context.args[0]  # <- pega o argumento

    if not re.fullmatch(r"[A-Za-z0-9_]{3,15}", username):
        await update.message.reply_text("❌ Nome inválido! Letras, números e _ de 3 a 15 caracteres.")
        return

    async with aiosqlite.connect(DB_FILE) as db:
        row = await db.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user_row = await row.fetchone()
        if user_row:
            await update.message.reply_text(
                f"❌ Você já definiu seu nome de usuário: {user_row[0]}"
            )
            return

    ok = await add_user(user_id, username)
    if not ok:
        await update.message.reply_text("❌ Este nome já está em uso. Escolha outro.")
    else:
        await update.message.reply_text(f"✅ Nome definido com sucesso: {username}")

# ---------- MAPA DE COMANDOS ---------- #
BOT_COMMANDS = {
    "start":    "Exibe a mensagem de boas‑vindas se por algum motivo você quiser vê-la novamente.",
    "username": "/username <nome> – define seu nome de usuário (só pode ser usado uma vez, escolha sabiamente).",
    "pull":     "Tente a sorte e ganhe uma carta que você provavelmente não quer.",
    "ajuda":    "Mostra esta lista de comandos XD.",
}

# ---------- HANDLER /ajuda ---------- #
async def ajuda_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    linhas = ["📜 *Comandos do HomuCards*"]
    for cmd, desc in BOT_COMMANDS.items():
        safe_desc = escape_text(desc)
        linhas.append(f"/{cmd} \\- {safe_desc}")
    texto = "\n".join(linhas)
    await update.message.reply_markdown_v2(texto)


# ---------- HANDLER /inventario ---------- #

async def inventario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    page = 0  # primeira página

    cartas, total = await get_user_inventory(user_id, ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)

    if not cartas:
        await update.message.reply_text("Seu inventário está vazio.")
        return

    texto = formatar_inventario_texto(cartas, page, total)
    teclado = montar_teclado_paginacao(page, total)

    await update.message.reply_text(texto, reply_markup=teclado)

async def inventario_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data  # exemplo: "inv_next_1", "inv_prev_2"
    user_id = query.from_user.id

    if not data.startswith("inv_"):
        return

    parts = data.split("_")
    if len(parts) != 3:
        return

    action, _, page_str = parts
    try:
        page = int(page_str)
    except ValueError:
        return

    if action == "inv_next":
        page += 1
    elif action == "inv_prev":
        page -= 1
    else:
        return

    if page < 0:
        page = 0

    cartas, total = await get_user_inventory(user_id, ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)
    texto = formatar_inventario_texto(cartas, page, total)
    teclado = montar_teclado_paginacao(page, total)

    await query.edit_message_text(texto, reply_markup=teclado)


async def removerid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Use: /removerid <id_da_carta>")
        return

    try:
        card_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID inválido! Use um número inteiro.")
        return

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "DELETE FROM cards WHERE id = ?", (card_id,)
        )
        await db.commit()

        if cursor.rowcount > 0:
            await update.message.reply_text(f"✅ Carta com ID {card_id} removida do banco.")
        else:
            await update.message.reply_text(f"⚠️ Carta com ID {card_id} não encontrada no banco.")
