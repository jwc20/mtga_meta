import csv
import sqlite3
from pathlib import Path

def find_project_root(marker=".git"):
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / marker).exists():
            return parent
    return current.parent

project_root = find_project_root()
db_path = project_root / "database.db"

def main():
    with open("cards_from_17_lands.csv", "r") as f, sqlite3.connect(db_path) as conn:
        reader = csv.reader(f)
        cursor = conn.cursor()
        for row in reader:
            print(row[0], row[2])
            cursor.execute("INSERT INTO cards_from_17_lands (mtgArenaId, name) VALUES (?, ?)", (row[0], row[2]))
        conn.commit()
        

if __name__ == "__main__":
    # main()
    import scrython

    card = scrython.cards.Named(fuzzy='Cecil, Dark Knight // Cecil, Redeemed Paladin')
    print(card)
    
    print("Done")
    
    
    
    
    
    
    
    
