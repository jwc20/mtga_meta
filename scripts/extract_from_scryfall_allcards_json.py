"""
https://scryfall.com/docs/api/cards
"""
import uuid
from pathlib import Path
import duckdb
from dataclasses import dataclass, asdict

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
output_dir = project_root / "card_data/scryfall"


@dataclass
class BaseCard:
    object: str
    id: str
    name: str


@dataclass
class CardIdentifiers:
    arena_id: int | None = None
    mtgo_id: int | None = None
    mtgo_foil_id: int | None = None
    multiverse_ids: list[int] | None = None
    resource_id: str | None = None
    oracle_id: str | None = None
    illustration_id: str | None = None


@dataclass
class CardAttributes:
    layout: str | None = None
    color_identity: list[str] | None = None
    colors: list[str] | None = None
    mana_cost: str | None = None
    type_line: str | None = None
    oracle_text: str | None = None


@dataclass
class CardMetadata:
    booster: bool | None = None
    rarity: str | None = None
    variation: bool | None = None
    games: list[str] | None = None
    promo_types: list[str] | None = None
    keywords: list[str] | None = None
    uri: str | None = None


@dataclass
class CoreCard(BaseCard):
    identifiers: CardIdentifiers
    attributes: CardAttributes
    metadata: CardMetadata
    printed_name: str | None = None
    printed_type_line: str | None = None
    printed_text: str | None = None
    printed_flavor_text: str | None = None
    flavor_name: str | None = None
    face_name: str | None = None
    cmc: float | None = None
    image_uri_large: dict | None = None


@dataclass
class RelatedCard(BaseCard):
    parent_id: str
    component: str
    type_line: str
    uri: str


@dataclass
class FaceCard(BaseCard):
    # parent_id: str | None = None
    mana_cost: str
    type_line: str | None = None
    oracle_text: str | None = None
    power: str | None = None
    toughness: str | None = None
    flavor_text: str | None = None
    artist: str | None = None
    artist_id: str | None = None
    illustration_id: str | None = None
    colors: list[str] | None = None
    image_uri_large: dict | None = None
    printed_name: str | None = None
    printed_type_line: str | None = None
    printed_text: str | None = None
    color_indicator: list[str] | None = None
    watermark: str | None = None
    defense: str | None = None
    loyalty: str | None = None
    oracle_id: str | None = None
    layout: str | None = None
    cmc: float | None = None
    flavor_name: str | None = None


def safe_get_value(df, i, column):
    value = df.at[i, column]
    if isinstance(value, (list, np.ndarray)):
        return value if len(value) > 0 else None
    elif isinstance(value, uuid.UUID):
        return str(value)
    elif pd.isna(value):
        return None
    return value


def get_all_arena_cards(all_cards: str) -> list[CoreCard]:
    result = []
    all_arena_cards = duckdb.sql(
        f"""
        SELECT object,
               id,
               arena_id,
               mtgo_id,
               mtgo_foil_id,
               multiverse_ids,
               resource_id,
               oracle_id,
               name,
               printed_name,
               printed_type_line,
               printed_text,
               flavor_name,
               layout,
               color_identity,
               colors,
               booster,
               rarity,
               mana_cost,
               type_line,
               variation,
               games,
               promo_types,
               illustration_id,
               uri,
               keywords,
               oracle_text,
               image_uris
        FROM '{all_cards}'
        where 'arena' in games and lang = 'en'; 
        """).fetchdf()

    for i in range(len(all_arena_cards)):
        identifiers = CardIdentifiers(
            arena_id=int(all_arena_cards.at[i, "arena_id"]) if pd.notna(all_arena_cards.at[i, "arena_id"]) else None,
            mtgo_id=int(all_arena_cards.at[i, "mtgo_id"]) if pd.notna(all_arena_cards.at[i, "mtgo_id"]) else None,
            mtgo_foil_id=int(all_arena_cards.at[i, "mtgo_foil_id"]) if pd.notna(
                all_arena_cards.at[i, "mtgo_foil_id"]) else None,
            multiverse_ids=safe_get_value(all_arena_cards, i, "multiverse_ids"),
            resource_id=str(all_arena_cards.at[i, "resource_id"]) if pd.notna(
                all_arena_cards.at[i, "resource_id"]) else None,
            oracle_id=safe_get_value(all_arena_cards, i, "oracle_id"),
            illustration_id=safe_get_value(all_arena_cards, i, "illustration_id")
        )

        attributes = CardAttributes(
            layout=safe_get_value(all_arena_cards, i, "layout"),
            color_identity=safe_get_value(all_arena_cards, i, "color_identity"),
            colors=safe_get_value(all_arena_cards, i, "colors"),
            mana_cost=safe_get_value(all_arena_cards, i, "mana_cost"),
            type_line=safe_get_value(all_arena_cards, i, "type_line"),
            oracle_text=safe_get_value(all_arena_cards, i, "oracle_text")
        )

        metadata = CardMetadata(
            booster=bool(all_arena_cards.at[i, "booster"]) if pd.notna(all_arena_cards.at[i, "booster"]) else None,
            rarity=safe_get_value(all_arena_cards, i, "rarity"),
            variation=bool(all_arena_cards.at[i, "variation"]) if pd.notna(
                all_arena_cards.at[i, "variation"]) else None,
            games=safe_get_value(all_arena_cards, i, "games"),
            promo_types=safe_get_value(all_arena_cards, i, "promo_types"),
            keywords=safe_get_value(all_arena_cards, i, "keywords"),
            uri=safe_get_value(all_arena_cards, i, "uri")
        )

        core_card = CoreCard(
            object=all_arena_cards.at[i, "object"],
            id=str(all_arena_cards.at[i, "id"]),
            name=all_arena_cards.at[i, "name"],
            identifiers=identifiers,
            attributes=attributes,
            metadata=metadata,
            image_uri_large=get_value_or_none(all_arena_cards, i, "image_uris.large")
        )

        result.append(core_card)

    return result


def get_value_or_none(df, index, column):
    value = df.at[index, column] if column in df.columns else None
    if value is None:
        return None
    if isinstance(value, (list, np.ndarray)):
        return value if len(value) > 0 else None
    elif isinstance(value, uuid.UUID):
        return str(value)
    elif isinstance(value, dict):
        return value if len(value) > 0 else None
    elif pd.isna(value):
        return None
    return value


def get_all_parts_cards(all_cards: str) -> list[RelatedCard]:
    result = []
    all_parts_cards = duckdb.sql(
        f"SELECT id, all_parts FROM '{all_cards}' where 'arena' in games and lang = 'en' and all_parts is not null").fetchdf()
    for parent_id, all_parts in zip(all_parts_cards["id"], all_parts_cards["all_parts"]):
        card_parts_dfs = pd.json_normalize(all_parts)
        for i in range(len(card_parts_dfs)):
            card_part = RelatedCard(
                object=card_parts_dfs.at[i, "object"],
                parent_id=str(parent_id),
                id=str(card_parts_dfs.at[i, "id"]),
                component=card_parts_dfs.at[i, "component"],
                name=card_parts_dfs.at[i, "name"],
                type_line=card_parts_dfs.at[i, "type_line"],
                uri=card_parts_dfs.at[i, "uri"]
            )
            result.append(card_part)
    return result


def get_all_card_faces(all_cards: str) -> list[FaceCard]:
    result = []
    all_card_faces_cards = duckdb.sql(
        f"SELECT id, card_faces FROM '{all_cards}' where 'arena' in games and lang = 'en' and card_faces is not null").fetchdf()
    for parent_id, all_parts in zip(all_card_faces_cards["id"], all_card_faces_cards["card_faces"]):
        card_parts_dfs = pd.json_normalize(all_parts)
        for i in range(len(card_parts_dfs)):
            card_face = FaceCard(
                object=card_parts_dfs.at[i, "object"],
                id=str(parent_id),
                # id=card_parts_dfs.at[i, "id"],
                name=card_parts_dfs.at[i, "name"],
                mana_cost=card_parts_dfs.at[i, "mana_cost"],
                type_line=get_value_or_none(card_parts_dfs, i, "type_line"),
                oracle_text=get_value_or_none(card_parts_dfs, i, "oracle_text"),
                power=get_value_or_none(card_parts_dfs, i, "power"),
                toughness=get_value_or_none(card_parts_dfs, i, "toughness"),
                flavor_text=get_value_or_none(card_parts_dfs, i, "flavor_text"),
                artist=get_value_or_none(card_parts_dfs, i, "artist"),
                artist_id=get_value_or_none(card_parts_dfs, i, "artist_id"),
                illustration_id=get_value_or_none(card_parts_dfs, i, "illustration_id"),
                colors=get_value_or_none(card_parts_dfs, i, "colors"),
                image_uri_large=get_value_or_none(card_parts_dfs, i, "image_uris.large"),
                printed_name=get_value_or_none(card_parts_dfs, i, "printed_name"),
                printed_type_line=get_value_or_none(card_parts_dfs, i, "printed_type_line"),
                printed_text=get_value_or_none(card_parts_dfs, i, "printed_text"),
                color_indicator=get_value_or_none(card_parts_dfs, i, "color_indicator"),
                watermark=get_value_or_none(card_parts_dfs, i, "watermark"),
                defense=get_value_or_none(card_parts_dfs, i, "defense"),
                loyalty=get_value_or_none(card_parts_dfs, i, "loyalty"),
                oracle_id=get_value_or_none(card_parts_dfs, i, "oracle_id"),
                layout=get_value_or_none(card_parts_dfs, i, "layout"),
                cmc=get_value_or_none(card_parts_dfs, i, "cmc"),
                flavor_name=get_value_or_none(card_parts_dfs, i, "flavor_name")
            )
            result.append(card_face)

    return result


# 
# def main():
#     all_cards = scryfall_allcards_json_file_path.__str__()
#     duckdb.read_json(all_cards)
# 
#     all_arena_cards = get_all_arena_cards(all_cards)  # all cards
#     all_parts_cards = get_all_parts_cards(all_cards)  # related cards
#     all_card_faces = get_all_card_faces(all_cards)  # card faces
# 
#     # output_data = {
#     #     "arena_cards": [asdict(card) for card in all_arena_cards],
#     #     "related_cards": [asdict(card) for card in all_parts_cards],
#     #     "face_cards": [asdict(card) for card in all_card_faces]
#     # }
#     # 
#     output_data = []
#     output_data.extend(all_arena_cards)
#     output_data.extend(all_parts_cards)
#     output_data.extend(all_card_faces)
# 
#     with open(output_dir / "new_all_cards.json", "w", encoding="utf-8") as f:
#         # use jsonpickle
#         json_str = jsonpickle.encode(output_data, unpicklable=False)
#         f.write(json_str)
# 
#     print("Wrote new_all_cards.json")


def flatten_dataclass(obj):
    base_dict = {
        "object": None,
        "id": None,
        "name": None,
        "parent_id": None,
        "component": None,
        "arena_id": None,
        "mtgo_id": None,
        "mtgo_foil_id": None,
        "multiverse_ids": None,
        "resource_id": None,
        "oracle_id": None,
        "illustration_id": None,
        "layout": None,
        "color_identity": None,
        "colors": None,
        "mana_cost": None,
        "type_line": None,
        "oracle_text": None,
        "booster": None,
        "rarity": None,
        "variation": None,
        "games": None,
        "promo_types": None,
        "keywords": None,
        "uri": None,
        "power": None,
        "toughness": None,
        "flavor_text": None,
        "artist": None,
        "artist_id": None,
        "image_uri_large": None,
        "printed_name": None,
        "printed_type_line": None,
        "printed_text": None,
        "color_indicator": None,
        "watermark": None,
        "defense": None,
        "loyalty": None,
        "cmc": None,
        "flavor_name": None,
        "card_type": None
    }

    if isinstance(obj, CoreCard):
        base_dict.update({
            "object": obj.object,
            "id": obj.id,
            "name": obj.name,
            "arena_id": obj.identifiers.arena_id,
            "mtgo_id": obj.identifiers.mtgo_id,
            "mtgo_foil_id": obj.identifiers.mtgo_foil_id,
            "multiverse_ids": obj.identifiers.multiverse_ids,
            "resource_id": obj.identifiers.resource_id,
            "oracle_id": obj.identifiers.oracle_id,
            "illustration_id": obj.identifiers.illustration_id,
            "layout": obj.attributes.layout,
            "color_identity": obj.attributes.color_identity,
            "colors": obj.attributes.colors,
            "mana_cost": obj.attributes.mana_cost,
            "type_line": obj.attributes.type_line,
            "oracle_text": obj.attributes.oracle_text,
            "booster": obj.metadata.booster,
            "rarity": obj.metadata.rarity,
            "variation": obj.metadata.variation,
            "games": obj.metadata.games,
            "promo_types": obj.metadata.promo_types,
            "keywords": obj.metadata.keywords,
            "uri": obj.metadata.uri,
        })
    elif isinstance(obj, RelatedCard):
        base_dict.update({
            "object": obj.object,
            "id": obj.id,
            "name": obj.name,
            "parent_id": obj.parent_id,
            "component": obj.component,
            "type_line": obj.type_line,
            "uri": obj.uri,
        })
    elif isinstance(obj, FaceCard):
        base_dict.update({
            "object": obj.object,
            "id": obj.id,
            "name": obj.name,
            "mana_cost": obj.mana_cost,
            "type_line": obj.type_line,
            "oracle_text": obj.oracle_text,
            "power": obj.power,
            "toughness": obj.toughness,
            "flavor_text": obj.flavor_text,
            "artist": obj.artist,
            "artist_id": obj.artist_id,
            "illustration_id": obj.illustration_id,
            "colors": obj.colors,
            "image_uri_large": obj.image_uri_large,
            "printed_name": obj.printed_name,
            "printed_type_line": obj.printed_type_line,
            "printed_text": obj.printed_text,
            "color_indicator": obj.color_indicator,
            "watermark": obj.watermark,
            "defense": obj.defense,
            "loyalty": obj.loyalty,
            "oracle_id": obj.oracle_id,
            "layout": obj.layout,
            "cmc": obj.cmc,
            "flavor_name": obj.flavor_name,
        })

    return base_dict


def main():
    all_cards = scryfall_allcards_json_file_path.__str__()
    duckdb.read_json(all_cards)

    all_arena_cards = get_all_arena_cards(all_cards)
    all_parts_cards = get_all_parts_cards(all_cards)
    all_card_faces = get_all_card_faces(all_cards)

    output_data = []
    output_data.extend([flatten_dataclass(card) for card in all_arena_cards])
    output_data.extend([flatten_dataclass(card) for card in all_parts_cards])
    output_data.extend([flatten_dataclass(card) for card in all_card_faces])

    with open(output_dir / "new_all_cards.json", "w", encoding="utf-8") as f:
        json_str = jsonpickle.encode(output_data, unpicklable=False)
        f.write(json_str)

    print(f"Wrote new_all_cards.json with {len(output_data)} cards")


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
