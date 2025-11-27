import sqlite3
import asyncio
from pathlib import Path
import json

from pprint import pprint


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

    # print(f'[{cmd!r} exited with {proc.returncode}]')
    # if stdout:
    #     print(f'[stdout]\n{stdout.decode()}')
    if stderr:
        print(f'[stderr]\n{stderr.decode()}')

    return stdout


async def get_data_from_scryfall():
    octosql_cli_query = f"octosql \"select id, arena_id, name, color_identity, colors, booster, rarity, mana_cost, card_faces, rarity, scryfall_uri, type_line, variation, games, promo_types, lang from {json_file_path.__str__()}\" --output json"

    # octosql_cli_query = f"octosql \"select * from {json_file_path.__str__()} where id='c976f89d-768a-4cee-b0ac-90f854bfe94f'\" --output json"

    # octosql_cli_query = f"octosql \"select * from {json_file_path.__str__()}\" --output json"
    
    print(octosql_cli_query)

    octosql_output = await asyncio.gather(run(octosql_cli_query))
    decoded_octosql_output = octosql_output[0].decode('utf-8')
    decoded_octosql_output_lines = decoded_octosql_output.split("\n")

    # decoded_json = json.load(decoded_octosql_output_lines)
    # print(decoded_json)

    count = 0
    result = []
    for line in decoded_octosql_output_lines:
        if line == "":
            continue
        count += 1
        card_object = json.loads(line)
        # print(o)
        if card_object["card_faces"]:
            card_object["card_faces"] = [face for face in card_object["card_faces"]]
        result.append(card_object)

    # print(result)
    print(count)
    return result


async def check_if_in_arena(cards):
    result = []
    count = 0
    for card in cards:
        if not card["games"] or "arena" not in card["games"] or card["lang"] != "en":
            continue
        if card["card_faces"]:
            card["card_faces"] = [face for face in card["card_faces"]]
            
        result.append(card)
        count += 1

    print(count)
    return result


async def store_to_db():
    conn = get_db()
    return


async def main():
    cards = await get_data_from_scryfall()
    # pprint(cards)
    arena_cards = await check_if_in_arena(cards)
    # pprint(arena_cards[123])
    # print([c["lang"] for c in arena_cards])
    with open("output_arena_cards.json", "w", encoding="utf-8") as wf:
        # json.dumps(arena_cards)
        # wf.write(json.dumps(arena_cards))
        for item in arena_cards:
            json_line = json.dumps(item)
            wf.write(json_line + '\n')
    print("Done")


if __name__ == "__main__":
    # main()

    asyncio.run(main())
