from telegram import Update
from telegram.ext import ContextTypes
from database.queries import add_user
import re
import aiosqlite
from config import DB_FILE, WELCOME_MESSAGE
from utils.formatters import escape_text

from database.queries import add_user

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
