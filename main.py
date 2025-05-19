import asyncio
import sys
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from handlers.commands import start, username_cmd, ajuda_cmd
from handlers.cards import pull_start, button_handler
from database.queries import load_series_and_cards
from config import BOT_TOKEN
from pathlib import Path
sys.path.append(str(Path(__file__).parent))

def setup_event_loop():
    """Configuração específica para Windows"""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def on_startup(app):
    """Tarefas de inicialização"""
    print("Iniciando caregamento de dados...")
    await load_series_and_cards()
    print("✅ Carregamento concluído")

def register_handlers(app):
    """Registra todos os handlers do bot"""
    handlers = [
        CommandHandler("start", start),
        CommandHandler("username", username_cmd),
        CommandHandler("pull", pull_start),
        CommandHandler("ajuda", ajuda_cmd),
        CallbackQueryHandler(button_handler)
    ]
    
    for handler in handlers:
        app.add_handler(handler)

def main():
    """Ponto principal de execução"""
    setup_event_loop()
    
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.post_init = on_startup
    
    register_handlers(app)
    
    print("🤖 Bot iniciado com sucesso")
    app.run_polling()

if __name__ == "__main__":
    main()