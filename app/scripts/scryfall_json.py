import sqlite3
import asyncio
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
    mana_cost: str
    name: str
    object: str
    oracle_text: str
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
    name: str
    color_identity: list[str]
    colors: list[str]
    booster: Optional[bool]
    rarity: str
    mana_cost: Optional[str]
    card_faces: Optional[list[CardFace]]
    scryfall_uri: str
    type_line: str
    variation: Optional[bool]
    games: list[str]
    promo_types: Optional[list[str]]
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


def dict_to_card(card_dict: dict) -> Card:
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
    octosql_cli_query = f"octosql \"select id, arena_id, name, color_identity, colors, booster, rarity, mana_cost, card_faces, scryfall_uri, type_line, variation, games, promo_types, lang from {json_file_path.__str__()}\" --output json"

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


async def store_to_db():
    conn = get_db()
    return


async def main():
    cards = await get_data_from_scryfall()
    arena_cards = await check_if_in_arena(cards)

    arena_cards_dicts = [card_to_dict(card) for card in arena_cards]

    with open("output_arena_cards.json", "w", encoding="utf-8") as wf:
        json.dump(arena_cards_dicts, wf, indent=2, ensure_ascii=False)

    print("Done")


if __name__ == "__main__":
    asyncio.run(main())