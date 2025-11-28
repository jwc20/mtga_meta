import sqlite3
import asyncio
import uuid
from pathlib import Path
import json
from dataclasses import dataclass, asdict
from typing import Optional

from pprint import pprint


@dataclass
class ImageUris:
    art_crop: str
    border_crop: str
    large: str
    normal: str
    png: str
    small: str


@dataclass
class CardFace:
    artist: str
    artist_id: str
    color_indicator: Optional[list[str]]
    colors: Optional[list[str]]
    flavor_text: Optional[str]
    illustration_id: Optional[str]
    image_uris: Optional[ImageUris]
    mana_cost: str | None
    name: str | None
    object: str | None
    oracle_text: str | None
    power: Optional[str]
    printed_name: Optional[str]
    printed_text: Optional[str]
    printed_type_line: Optional[str]
    toughness: Optional[str]
    type_line: str


@dataclass
class Card:
    id: str
    arena_id: Optional[int]
    name: str | None
    color_identity: list[str]
    colors: list[str] | None
    booster: Optional[bool]
    rarity: str | None
    mana_cost: Optional[str]
    card_faces: Optional[list[CardFace]]
    scryfall_uri: str | None
    type_line: str | None
    variation: Optional[bool]
    games: list[str]
    promo_types: Optional[list[str]]
    illustration_id: Optional[str]
    image_uris: Optional[ImageUris]
    lang: str


def find_project_root(marker=".git"):
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent
    return current.parent


def get_db():
    _conn = sqlite3.connect(db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    return _conn


project_root = find_project_root()
db_path = project_root / "database.db"
json_file_path = project_root / "app/scripts/allcardso.json"


async def run(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)

    stdout, stderr = await proc.communicate()

    if stderr:
        print(f'[stderr]\n{stderr.decode()}')

    return stdout


def convert_null_strings(obj):
    if isinstance(obj, dict):
        return {k: convert_null_strings(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_null_strings(item) for item in obj]
    elif obj == "null":
        return None
    else:
        return obj


def dict_to_card(card_dict: dict) -> Card:
    card_dict = convert_null_strings(card_dict)

    if card_dict.get("image_uris"):
        card_dict["image_uris"] = ImageUris(**card_dict["image_uris"])

    if card_dict.get("card_faces"):
        card_faces = []
        for face_dict in card_dict["card_faces"]:
            image_uris = None
            if face_dict.get("image_uris"):
                image_uris = ImageUris(**face_dict["image_uris"])

            card_face = CardFace(
                artist=face_dict["artist"],
                artist_id=face_dict["artist_id"],
                color_indicator=face_dict.get("color_indicator"),
                colors=face_dict.get("colors"),
                flavor_text=face_dict.get("flavor_text"),
                illustration_id=face_dict.get("illustration_id"),
                image_uris=image_uris,
                mana_cost=face_dict["mana_cost"],
                name=face_dict["name"],
                object=face_dict["object"],
                oracle_text=face_dict["oracle_text"],
                power=face_dict.get("power"),
                printed_name=face_dict.get("printed_name"),
                printed_text=face_dict.get("printed_text"),
                printed_type_line=face_dict.get("printed_type_line"),
                toughness=face_dict.get("toughness"),
                type_line=face_dict["type_line"]
            )
            card_faces.append(card_face)
        card_dict["card_faces"] = card_faces

    return Card(**card_dict)


def card_to_dict(card: Card) -> dict:
    result = asdict(card)
    return result


async def get_data_from_scryfall():
    octosql_cli_query = f"octosql \"select id, arena_id, name, color_identity, colors, booster, rarity, mana_cost, card_faces, scryfall_uri, type_line, variation, games, promo_types, lang, illustration_id, image_uris from {json_file_path.__str__()}\" --output json"

    print(octosql_cli_query)

    octosql_output = await asyncio.gather(run(octosql_cli_query))
    decoded_octosql_output = octosql_output[0].decode('utf-8')
    decoded_octosql_output_lines = decoded_octosql_output.split("\n")

    count = 0
    result = []
    for line in decoded_octosql_output_lines:
        if line == "":
            continue
        count += 1
        card_dict = json.loads(line)
        card = dict_to_card(card_dict)
        result.append(card)

    print(count)
    return result


async def check_if_in_arena(cards: list[Card]):
    result = []
    count = 0
    for card in cards:
        if not card.games or "arena" not in card.games or card.lang != "en":
            continue

        result.append(card)
        count += 1

    print(count)
    return result


async def create_cards_table(conn):
    cursor = conn.cursor()
    cursor.execute("Drop Table IF EXISTS scryfall_arena_cards")
    conn.commit()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scryfall_arena_cards (
            id TEXT PRIMARY KEY,
            arena_id INTEGER,
            name TEXT NOT NULL,
            color_identity TEXT,
            colors TEXT,
            booster INTEGER,
            rarity TEXT,
            mana_cost TEXT,
            card_faces TEXT,
            scryfall_uri TEXT,
            type_line TEXT,
            variation INTEGER,
            games TEXT,
            promo_types TEXT,
            lang TEXT NOT NULL,
            illustration_id TEXT,
            image_uris TEXT
        )
    """)
    conn.commit()


async def insert_cards_to_db(conn, cards: list[Card]):
    cursor = conn.cursor()

    for card in cards:
        card_dict = asdict(card)

        cursor.execute("""
            INSERT OR REPLACE INTO scryfall_arena_cards (
                id, arena_id, name, color_identity, colors, booster, 
                rarity, mana_cost, card_faces, scryfall_uri, type_line, 
                variation, games, promo_types, lang, illustration_id, image_uris
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card_dict["id"],
            card_dict["arena_id"],
            card_dict["name"],
            json.dumps(card_dict["color_identity"]),
            json.dumps(card_dict["colors"]),
            card_dict["booster"],
            card_dict["rarity"],
            card_dict["mana_cost"],
            json.dumps(card_dict["card_faces"]) if card_dict["card_faces"] else None,
            card_dict["scryfall_uri"],
            card_dict["type_line"],
            card_dict["variation"],
            json.dumps(card_dict["games"]),
            json.dumps(card_dict["promo_types"]) if card_dict["promo_types"] else None,
            card_dict["lang"],
            card_dict["illustration_id"],
            json.dumps(card_dict["image_uris"]) if card_dict["image_uris"] else None,
        ))

    conn.commit()
    print(f"Inserted {len(cards)} cards into database")


def write_json_file(cards: list[Card]):
    arena_cards_dicts = [asdict(card) for card in cards]
    with open("output_arena_cards.json", "w", encoding="utf-8") as wf:
        json.dump(arena_cards_dicts, wf, indent=2, ensure_ascii=False)
    print("Wrote JSON file")


async def store_to_db(cards: list[Card]):
    conn = get_db()
    await create_cards_table(conn)
    await insert_cards_to_db(conn, cards)
    conn.close()


async def main():
    cards = await get_data_from_scryfall()
    arena_cards = await check_if_in_arena(cards)

    final_cards = []
    seen_illustration_ids = set()

    for card in arena_cards:
        if not card.arena_id and card.card_faces:
            for face in card.card_faces:
                if face.illustration_id and face.illustration_id in seen_illustration_ids:
                    continue

                face_card = Card(
                    id=uuid.uuid4().hex,
                    arena_id=card.arena_id,
                    name=face.name,
                    color_identity=card.color_identity,
                    colors=face.colors if face.colors else card.colors,
                    booster=card.booster,
                    rarity=card.rarity,
                    mana_cost=face.mana_cost,
                    card_faces=None,
                    scryfall_uri=card.scryfall_uri,
                    type_line=face.type_line,
                    variation=card.variation,
                    games=card.games,
                    promo_types=card.promo_types,
                    lang=card.lang,
                    illustration_id=face.illustration_id,
                    image_uris=face.image_uris
                )

                if face.illustration_id:
                    seen_illustration_ids.add(face.illustration_id)

                final_cards.append(face_card)

        final_cards.append(card)

    await store_to_db(final_cards)

    print("Done")


if __name__ == "__main__":
    asyncio.run(main())