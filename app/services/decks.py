import aiosqlite
from datetime import datetime


async def get_decks(cursor: aiosqlite.Cursor) -> list[dict]:
    await cursor.execute("""
    SELECT d.id        as deck_id,
           d.name      as deck_name,
           d.source    as deck_source,
           d.url       as deck_url,
           c.name      as name,
           dc.quantity as quantity,
           c.mana_cost as mana_cost,
           c.type_line as type_line,
           c.component as component
    FROM decks d
             INNER JOIN deck_cards dc
                        ON d.id = dc.deck_id
             Inner JOIN scryfall_all_cards c
                       ON dc.card_id = c.id
    ORDER BY added_at DESC
    LIMIT 100;
    """)
    rows = await cursor.fetchall()

    cards = [dict(row) for row in rows]
    decks = {}

    cards = [card for card in cards if card["component"] != "combo_piece"]

    for card in cards:
        deck_id = card["deck_id"]

        if deck_id not in decks:
            decks[deck_id] = {
                "id": card["deck_id"],
                "name": card["deck_name"],
                "source": card["deck_source"],
                "url": card["deck_url"],
                "cards": []
            }

        card_info = {
            "name": card["name"],
            "quantity": card["quantity"],
            "mana_cost": card["mana_cost"],
            "type_line": card["type_line"]
        }
        decks[deck_id]["cards"].append(card_info)

    return list(decks.values())


async def add_decks_to_db(conn: aiosqlite.Connection, decks: list) -> None:
    cursor = await conn.cursor()

    for deck in decks:
        if deck.get("error"):
            print(f"Skipping deck {deck['name']} due to error: {deck['error']}")
            continue

        try:
            await cursor.execute(
                "INSERT INTO decks (name, source, url, added_at) VALUES (?, ?, ?, ?)",
                (deck["name"], "untapped", deck["url"], datetime.now())
            )
            await conn.commit()
        except aiosqlite.IntegrityError:
            print(f"Deck {deck['name']} already exists in database")
            continue
        except Exception as e:
            print(f"Error adding deck {deck['name']} to database: {e}")
            continue

        deck_id = cursor.lastrowid

        for card in deck.get("cards", []):
            await cursor.execute(
                "SELECT id FROM scryfall_all_cards WHERE name = ?",
                (card["name"],)
            )
            result = await cursor.fetchone()

            if not result:
                print(f"Card {card['name']} not found in database")
                await cursor.execute(
                    "SELECT id FROM scryfall_all_cards WHERE printed_name LIKE ? OR flavor_name LIKE ?",
                    (card["name"], card["name"]))
                result = await cursor.fetchone()

            card_id = result[0]
            await cursor.execute(
                "INSERT OR IGNORE INTO deck_cards (deck_id, card_id, quantity, name, section) VALUES (?, ?, ?, ?, ?)",
                (deck_id, card_id, card.get("qty", 1), card["name"], "main")
            )
            await conn.commit()
