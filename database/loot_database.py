#!/usr/bin/env python3
"""
Loot Database - Wrapper for loot_index.json.

Provides filtering and lookup for items and their drop sources (enemies/biomes).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass

_DATABASE_DIR = Path(__file__).parent
_LOOT_FILE = _DATABASE_DIR / "data" / "loot_index.json"


@dataclass
class LootItem:
    """Represents a loot item."""
    name: str
    biomes: List[str]      # Biomes where this drops
    enemies: List[str]     # Enemies that drop this
    category: str          # e.g. "white_bag", "potion", etc

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "biomes": self.biomes,
            "enemies": self.enemies,
            "category": self.category
        }


@dataclass
class LootDropper:
    """Represents an enemy that drops loot."""
    name: str
    biomes: List[str]      # Biomes this enemy is found in
    items: List[str]       # Items this enemy drops
    category: str = "monster"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "biomes": self.biomes,
            "items": self.items,
            "category": self.category
        }


class LootDatabase:
    """
    Database for loot lookups.

    Usage:
        db = LootDatabase()
        
        # Get item details
        item = db.get_item("Doom's Emblem")
        
        # Find all white bags in a biome
        items = db.get_biome_loot("risen_hell", category="white_bag")
        
        # Find what an enemy drops
        items = db.get_enemy_drops("Red Demon")
    """

    def __init__(self, loot_file: Path = _LOOT_FILE):
        self.loot_file = loot_file
        self.items: Dict[str, LootItem] = {}
        self.enemies: Dict[str, LootDropper] = {}
        self._load()

    def _load(self):
        """Load loot index from JSON."""
        if not self.loot_file.exists():
            print(f"[WARN] Loot file not found: {self.loot_file}")
            return

        try:
            with open(self.loot_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load loot index: {e}")
            return

        # Load Items
        for name, info in data.get('items', {}).items():
            self.items[name] = LootItem(
                name=name,
                biomes=info.get('biomes', []),
                enemies=info.get('enemies', []),
                category=info.get('category', 'unknown')
            )

        # Load Enemies
        for name, info in data.get('enemies', {}).items():
            self.enemies[name] = LootDropper(
                name=name,
                biomes=info.get('biomes', []),
                items=info.get('items', []),
                category=info.get('category', 'monster')
            )

    def get_item(self, name: str) -> Optional[LootItem]:
        """Get item details by name."""
        return self.items.get(name)

    def get_dropper(self, name: str) -> Optional[LootDropper]:
        """Get loot dropper (enemy) details by name."""
        return self.enemies.get(name)

    def search_items(self, query: str) -> List[LootItem]:
        """Fuzzy search for items."""
        q = query.lower()
        return [item for name, item in self.items.items() if q in name.lower()]

    def get_enemy_drops(self, enemy_name: str) -> List[LootItem]:
        """Get all items dropped by a specific enemy."""
        dropper = self.enemies.get(enemy_name)
        if not dropper:
            return []
        
        drops = []
        for item_name in dropper.items:
            item = self.items.get(item_name)
            if item:
                drops.append(item)
        return drops

    def get_biome_loot(self, biome_slug: str, category: str = None) -> List[LootItem]:
        """
        Get all loot available in a biome.
        
        This finds all items where the item's 'biomes' list contains the target biome.
        """
        results = []
        for item in self.items.values():
            if biome_slug in item.biomes:
                if category and item.category != category:
                    continue
                results.append(item)
        return results

    def get_dungeon_loot(self, dungeon_enemies: List[str], category: str = None) -> List[LootItem]:
        """
        Get all loot dropped by a list of enemies (e.g. from a dungeon).
        """
        results = set() # Use set names to dedupe
        final_items = []
        
        for enemy_name in dungeon_enemies:
            dropper = self.enemies.get(enemy_name)
            if not dropper:
                continue
                
            for item_name in dropper.items:
                if item_name in results:
                    continue
                    
                item = self.items.get(item_name)
                if item:
                    if category and item.category != category:
                        continue
                    results.add(item_name)
                    final_items.append(item)
                    
        return final_items

if __name__ == "__main__":
    db = LootDatabase()
    print(f"Loaded {len(db.items)} items and {len(db.enemies)} enemies")
    
    demon_drops = db.get_enemy_drops("Red Demon")
    print(f"Red Demon drops: {[i.name for i in demon_drops]}")
    
    hell_loot = db.get_biome_loot("risen_hell", category="white_bag")
    print(f"Risen Hell White Bags: {[i.name for i in hell_loot]}")
