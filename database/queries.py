import aiosqlite
import os
import random
from pathlib import Path
from config import DB_FILE, CARDS_DIR
from utils.image_cache import load_image


# ---------- FUNÇÕES DATABASE ---------- #
async def init_db():
    """Cria as tabelas se ainda não existirem."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                series_id INTEGER NOT NULL,
                card_name TEXT NOT NULL,
                filename TEXT NOT NULL,
                order_in_series INTEGER,
                FOREIGN KEY (series_id) REFERENCES series(id),
                UNIQUE(series_id, card_name)
            );

            CREATE TABLE IF NOT EXISTS user_cards (
                user_id INTEGER,
                card_id INTEGER,
                quantity INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, card_id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (card_id) REFERENCES cards(id)
            );
            
            CREATE TABLE IF NOT EXISTS user_wallet (
                user_id INTEGER PRIMARY KEY,
                total_pulls INTEGER DEFAULT 0,
                last_diaria TIMESTAMP NULL,
                last_horaria TIMESTAMP NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            """
        )
        await db.commit()


async def add_user(user_id: int, username: str) -> bool:
    """Tenta inserir um novo usuário. Retorna True se OK, False se username existir."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT 1 FROM users WHERE LOWER(username)=LOWER(?)", (username,)
        )
        row = await cursor.fetchone()
        if row:
            return False
        await db.execute(
            "INSERT INTO users (id, username) VALUES (?, ?)", (user_id, username)
        )
        await db.commit()
        return True
    
    
async def load_series_and_cards():
    print("Iniciando carga de séries e cartas...")
    
    # Verificação inicial da pasta principal
    if not os.path.exists(CARDS_DIR):
        raise FileNotFoundError(f"Diretório de cartas não encontrado: {CARDS_DIR}")

    async with aiosqlite.connect(DB_FILE) as db:
        # Primeiro loop: processa apenas diretórios válidos
        for series_name in os.listdir(CARDS_DIR):
            series_path = os.path.join(CARDS_DIR, series_name)
            
            if not os.path.isdir(series_path):  # Ignora arquivos
                print(f"Ignorando arquivo: {series_name}")
                continue

            print(f"Processando série: {series_name}")
            
            try:
                # Insere a série no banco
                await db.execute(
                    "INSERT OR IGNORE INTO series (name) VALUES (?)",
                    (series_name,),
                )
                await db.commit()

                # Obtém o ID da série
                cursor = await db.execute(
                    "SELECT id FROM series WHERE name = ?", (series_name,)
                )
                series_row = await cursor.fetchone()
                if not series_row:
                    print(f"Erro ao obter ID para série: {series_name}")
                    continue
                    
                series_id = series_row[0]

                # Processa as cartas
                card_count = 0
                for filename in os.listdir(series_path):
                    if not filename.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                        continue
                        
                    card_name = Path(filename).stem
                    card_count += 1

                    await db.execute(
                        """
                        INSERT OR IGNORE INTO cards 
                        (series_id, card_name, filename, order_in_series)
                        VALUES (?, ?, ?, ?)
                        """,
                        (series_id, card_name, filename, card_count),
                    )
                
                await db.commit()
                print(f"✅ {series_name}: {card_count} cartas processadas")

            except Exception as e:
                print(f"❌ Erro na série {series_name}: {str(e)}")
                continue

    # Pré-carregamento separado (opcional)
    print("Pré-carregando imagens...")
    for series in os.listdir(CARDS_DIR):
        series_path = os.path.join(CARDS_DIR, series)
        if os.path.isdir(series_path):
            for card in os.listdir(series_path):
                if card.lower().endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        load_image(os.path.join(series_path, card))
                    except Exception as e:
                        print(f"Erro ao pré-carregar {card}: {e}")


async def pull_card_from_series(user_id: int, series_name: str):
    async with aiosqlite.connect(DB_FILE) as db:
        # Pega o id da série
        cursor = await db.execute(
            "SELECT id FROM series WHERE LOWER(name) = LOWER(?)",
            (series_name,)
        )
        row = await cursor.fetchone()
        if not row:
            return None, None, None
        series_id = row[0]

        # Busca cartas da série, ordenadas por order_in_series
        cursor = await db.execute(
            """
            SELECT id, card_name, filename
            FROM cards
            WHERE series_id = ?
            ORDER BY order_in_series ASC
            """,
            (series_id,)
        )
        cards = await cursor.fetchall()
        if not cards:
            return None, None, None

        # Sorteia uma carta
        card = random.choice(cards)
        card_id, card_name, filename = card
        return card_id, card_name, filename


async def add_card_to_user(user_id, card_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(
            """
            INSERT INTO user_cards (user_id, card_id, quantity)
            VALUES (?, ?, 1)
            ON CONFLICT(user_id, card_id)
            DO UPDATE SET quantity = quantity + 1;
            """,
            (user_id, card_id),
        )
        await db.commit()


async def get_card_count_for_user(user_id, card_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            "SELECT quantity FROM user_cards WHERE user_id=? AND card_id=?",
            (user_id, card_id),
        )
        row = await cursor.fetchone()
    return row[0] if row else 0

async def get_user_inventory(user_id: int, limit: int, offset: int):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            """
            SELECT c.id, c.name, uc.quantity
            FROM cards c
            JOIN user_cards uc ON c.id = uc.card_id
            WHERE uc.user_id = ?
            ORDER BY c.name
            LIMIT ? OFFSET ?
            """,
            (user_id, limit, offset)
        )
        rows = await cursor.fetchall()

        # Também busca total para saber se tem mais páginas
        cursor2 = await db.execute(
            "SELECT COUNT(*) FROM user_cards WHERE user_id = ?", (user_id,)
        )
        total_count = (await cursor2.fetchone())[0]

    return rows, total_count
