"""
https://scryfall.com/docs/api/cards
"""
import sqlite3
import uuid
from pathlib import Path
from dataclasses import dataclass, fields

import duckdb
import numpy as np
import pandas as pd
import jsonpickle


def find_project_root(marker=".git"):
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent
    return current.parent


project_root = find_project_root()
scryfall_allcards_json_file_path = project_root / "card_data/scryfall/allcards.json"
new_scryfall_allcards_json_file_path = project_root / "card_data/scryfall/allcards_arena.json"
json_output_dir = project_root / "card_data/scryfall"
db_path = project_root / "database.db"


@dataclass
class CoreCard:
    object: str
    id: uuid.UUID
    name: str
    arena_id: int | None = None
    mtgo_id: int | None = None
    mtgo_foil_id: int | None = None
    multiverse_ids: list[int] | None = None
    resource_id: str | None = None
    oracle_id: uuid.UUID | None = None
    illustration_id: uuid.UUID | None = None
    layout: str | None = None
    color_identity: list[str] | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    type_line: str | None = None
    oracle_text: str | None = None
    booster: bool | None = None
    rarity: str | None = None
    variation: bool | None = None
    games: list[str] | None = None
    promo_types: list[str] | None = None
    keywords: list[str] | None = None
    uri: str | None = None
    printed_name: str | None = None
    printed_type_line: str | None = None
    printed_text: str | None = None
    printed_flavor_text: str | None = None
    flavor_name: str | None = None
    face_name: str | None = None
    # cmc: float | None = None
    image_uri_large: str | None = None


@dataclass
class RelatedCard:
    object: str
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID
    component: str
    type_line: str
    uri: str


@dataclass
class FaceCard:
    object: str
    id: uuid.UUID
    name: str
    mana_cost: str
    type_line: str | None = None
    oracle_text: str | None = None
    power: str | None = None
    toughness: str | None = None
    flavor_text: str | None = None
    artist: str | None = None
    artist_id: uuid.UUID | None = None
    illustration_id: uuid.UUID | None = None
    colors: list[str] | None = None
    image_uri_large: str | None = None
    printed_name: str | None = None
    printed_type_line: str | None = None
    printed_text: str | None = None
    color_indicator: list[str] | None = None
    watermark: str | None = None
    defense: str | None = None
    loyalty: str | None = None
    oracle_id: uuid.UUID | None = None
    layout: str | None = None
    # cmc: float | None = None
    flavor_name: str | None = None


def to_uuid(value) -> uuid.UUID | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        return uuid.UUID(value)
    return None


def get_value(df, index: int, column: str):
    if column not in df.columns:
        return None
    value = df.at[index, column]
    if isinstance(value, float) and pd.isna(value):
        return None
    if isinstance(value, (list, np.ndarray)):
        return value if len(value) > 0 else None
    if isinstance(value, dict):
        return value if len(value) > 0 else None
    return value


def get_int(df, index: int, column: str) -> int | None:
    value = get_value(df, index, column)
    if pd.isna(value):
        return None
    return int(value) if value is not None else None


def get_bool(df, index: int, column: str) -> bool | None:
    value = get_value(df, index, column)
    if pd.isna(value):
        return None
    return bool(value) if value is not None else None


def get_uuid(df, index: int, column: str) -> uuid.UUID | None:
    return to_uuid(get_value(df, index, column))


def get_all_arena_cards(all_cards: str) -> list[CoreCard]:
    result = []
    df = duckdb.sql(f"""
        SELECT object, id, arena_id, mtgo_id, mtgo_foil_id, multiverse_ids,
               resource_id, oracle_id, name, printed_name, printed_type_line,
               printed_text, flavor_name, layout, color_identity, colors,
               booster, rarity, mana_cost, type_line, variation, games,
               promo_types, illustration_id, uri, keywords, oracle_text, image_uris
        FROM '{all_cards}'
        WHERE 'arena' IN games AND lang = 'en'
    """).fetchdf()

    for i in range(len(df)):
        card = CoreCard(
            object=get_value(df, i, "object"),
            id=to_uuid(df.at[i, "id"]),
            name=get_value(df, i, "name"),
            arena_id=get_int(df, i, "arena_id"),
            mtgo_id=get_int(df, i, "mtgo_id"),
            mtgo_foil_id=get_int(df, i, "mtgo_foil_id"),
            multiverse_ids=get_value(df, i, "multiverse_ids"),
            resource_id=get_value(df, i, "resource_id"),
            oracle_id=get_uuid(df, i, "oracle_id"),
            illustration_id=get_uuid(df, i, "illustration_id"),
            layout=get_value(df, i, "layout"),
            color_identity=get_value(df, i, "color_identity"),
            colors=get_value(df, i, "colors"),
            mana_cost=get_value(df, i, "mana_cost"),
            type_line=get_value(df, i, "type_line"),
            oracle_text=get_value(df, i, "oracle_text"),
            booster=get_bool(df, i, "booster"),
            rarity=get_value(df, i, "rarity"),
            variation=get_bool(df, i, "variation"),
            games=get_value(df, i, "games"),
            promo_types=get_value(df, i, "promo_types"),
            keywords=get_value(df, i, "keywords"),
            uri=get_value(df, i, "uri"),
            printed_name=get_value(df, i, "printed_name"),
            printed_type_line=get_value(df, i, "printed_type_line"),
            printed_text=get_value(df, i, "printed_text"),
            image_uri_large=get_value(df, i, "image_uris.large")
        )
        result.append(card)

    return result


def get_all_parts_cards(all_cards: str) -> list[RelatedCard]:
    result = []
    df = duckdb.sql(f"""
        SELECT id, all_parts 
        FROM '{all_cards}' 
        WHERE 'arena' IN games AND lang = 'en' AND all_parts IS NOT NULL
    """).fetchdf()

    for parent_id, related_parts in zip(df["id"], df["all_parts"]):
        parts_df = pd.json_normalize(related_parts)
        for i in range(len(parts_df)):
            card = RelatedCard(
                object=get_value(parts_df, i, "object"),
                id=to_uuid(parts_df.at[i, "id"]),
                name=get_value(parts_df, i, "name"),
                parent_id=to_uuid(parent_id),
                component=get_value(parts_df, i, "component"),
                type_line=get_value(parts_df, i, "type_line"),
                uri=get_value(parts_df, i, "uri"),
            )
            result.append(card)

    return result


def get_all_card_faces(all_cards: str) -> list[FaceCard]:
    result = []
    df = duckdb.sql(f"""
        SELECT id, card_faces 
        FROM '{all_cards}' 
        WHERE 'arena' IN games AND lang = 'en' AND card_faces IS NOT NULL
    """).fetchdf()

    for parent_id, faces in zip(df["id"], df["card_faces"]):
        faces_df = pd.json_normalize(faces)
        for i in range(len(faces_df)):
            card = FaceCard(
                object=get_value(faces_df, i, "object"),
                id=to_uuid(parent_id),
                name=get_value(faces_df, i, "name"),
                mana_cost=get_value(faces_df, i, "mana_cost"),
                type_line=get_value(faces_df, i, "type_line"),
                oracle_text=get_value(faces_df, i, "oracle_text"),
                power=get_value(faces_df, i, "power"),
                toughness=get_value(faces_df, i, "toughness"),
                flavor_text=get_value(faces_df, i, "flavor_text"),
                artist=get_value(faces_df, i, "artist"),
                artist_id=get_uuid(faces_df, i, "artist_id"),
                illustration_id=get_uuid(faces_df, i, "illustration_id"),
                colors=get_value(faces_df, i, "colors"),
                image_uri_large=get_value(faces_df, i, "image_uris.large"),
                printed_name=get_value(faces_df, i, "printed_name"),
                printed_type_line=get_value(faces_df, i, "printed_type_line"),
                printed_text=get_value(faces_df, i, "printed_text"),
                color_indicator=get_value(faces_df, i, "color_indicator"),
                watermark=get_value(faces_df, i, "watermark"),
                defense=get_value(faces_df, i, "defense"),
                loyalty=get_value(faces_df, i, "loyalty"),
                oracle_id=get_uuid(faces_df, i, "oracle_id"),
                layout=get_value(faces_df, i, "layout"),
                # cmc=get_value(faces_df, i, "cmc"),
                flavor_name=get_value(faces_df, i, "flavor_name"),
            )
            result.append(card)

    return result


ALL_FIELDS = [
    "object", "id", "name", "parent_id", "component", "arena_id", "mtgo_id",
    "mtgo_foil_id", "multiverse_ids", "resource_id", "oracle_id", "illustration_id",
    "layout", "color_identity", "colors", "mana_cost", "type_line", "oracle_text",
    "booster", "rarity", "variation", "games", "promo_types", "keywords", "uri",
    "power", "toughness", "flavor_text", "artist", "artist_id", "image_uri_large",
    "printed_name", "printed_type_line", "printed_text", "color_indicator",
    "watermark", "defense", "loyalty", "flavor_name", "card_type",
    "printed_flavor_text", "face_name",
]


# def flatten_dataclass(obj) -> dict:
#     result = {field: None for field in ALL_FIELDS}
#     for field in fields(obj):
#         value = getattr(obj, field.name)
#         if isinstance(value, uuid.UUID):
#             value = str(value)
#         result[field.name] = value
#     return result
# 
# 
# def main():
#     all_cards = str(scryfall_allcards_json_file_path)
#     duckdb.read_json(all_cards)
# 
#     all_arena_cards = get_all_arena_cards(all_cards)
#     all_parts_cards = get_all_parts_cards(all_cards)
#     all_card_faces = get_all_card_faces(all_cards)
# 
#     output_data = [
#         flatten_dataclass(card)
#         for card in (*all_arena_cards, *all_parts_cards, *all_card_faces)
#     ]
# 
#     with open(output_dir / "new_all_cards.json", "w", encoding="utf-8") as f:
#         json_str = jsonpickle.encode(output_data, unpicklable=False)
#         f.write(json_str)
# 
#     print(f"Wrote new_all_cards.json with {len(output_data)} cards")


def flatten_dataclass(obj) -> dict:
    result = {field: None for field in ALL_FIELDS}
    for field in fields(obj):
        value = getattr(obj, field.name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, (list, np.ndarray)):
            # value = ",".join(str(v) for v in value) if value else None
            value = ",".join(str(v) for v in value) if len(value) > 0 else None
        result[field.name] = value
    return result


def create_table(conn: sqlite3.Connection):
    columns = ", ".join(f"{field} TEXT" for field in ALL_FIELDS)
    conn.execute(f"DROP TABLE IF EXISTS scryfall_all_cards")
    conn.execute(f"CREATE TABLE scryfall_all_cards ({columns})")


def insert_cards(conn: sqlite3.Connection, cards: list[dict]):
    placeholders = ", ".join("?" for _ in ALL_FIELDS)

    def sanitize(value):
        if value is None or pd.isna(value):
            return None
        return value

    conn.executemany(
        f"INSERT INTO scryfall_all_cards VALUES ({placeholders})",
        [tuple(sanitize(card[field]) for field in ALL_FIELDS) for card in cards]
    )


def main():
    all_cards = str(scryfall_allcards_json_file_path)
    duckdb.read_json(all_cards)

    all_arena_cards = get_all_arena_cards(all_cards)
    all_parts_cards = get_all_parts_cards(all_cards)
    all_card_faces = get_all_card_faces(all_cards)

    output_data = [
        flatten_dataclass(card)
        for card in (*all_arena_cards, *all_parts_cards, *all_card_faces)
    ]

    with sqlite3.connect(db_path) as conn:
        create_table(conn)
        insert_cards(conn, output_data)
        conn.commit()

    print(f"Inserted {len(output_data)} cards into {db_path}")

if __name__ == "__main__":
    main()