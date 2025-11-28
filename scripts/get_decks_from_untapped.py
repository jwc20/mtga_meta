
deck_str = """
About
Name Mono-White

Deck
20 Plains
4 Ethereal Armor
4 Spellbook Vendor
4 Feather of Flight
4 Optimistic Scavenger
4 Shardmage's Rescue
4 Sheltered by Ghosts
4 Veteran Survivor
4 Seam Rip
4 A Most Helpful Weaver
4 Wonderweave Aerialist
"""

def main():
    deck_str_list = deck_str.strip().split("\n")
    deck_name = deck_str_list[1].strip().split(" ")[1]
    deck_cards = deck_str_list[4:]
    
    deck_dict = {"name": deck_name, "cards": {}}
    
    for card in deck_cards:
        card_name = " ".join(card.split(" ")[1:])
        card_count = card.split(" ")[0]
        deck_dict["cards"][card_name] = card_count
    
    return deck_dict


if __name__ == "__main__":
    d = main()
    print(d)