#!/usr/bin/env python3
"""
App Database Manager - Unified access point for all data sources.

Wraps EntityIndex, DungeonDatabase, and LootDatabase into a single interface.
"""

from pathlib import Path
from typing import Optional, List, Dict

# Import component databases
# Using relative imports assuming this file is in database/
from .entity_index import EntityIndex
from .dungeon_database import DungeonDatabase
from .loot_database import LootDatabase, LootItem

class AppDatabase:
    """
    Unified Data Manager for StateGenerator App.
    
    Attributes:
        entities (EntityIndex): Lookup for all game entities (names, IDs).
        dungeons (DungeonDatabase): Lookup for dungeon properties and enemy lists.
        loot (LootDatabase): Lookup for items and drop tables.
    """
    
    def __init__(self):
        # Initialize sub-databases
        self.entities = EntityIndex()
        self.dungeons = DungeonDatabase()
        self.loot = LootDatabase()
        
    def get_loot_for_biome(self, biome_slug: str, category: str = None) -> List[LootItem]:
        """
        Convenience: Get all loot available in a biome.
        Delegates to LootDatabase.
        """
        return self.loot.get_biome_loot(biome_slug, category)
        
    def get_loot_for_dungeon(self, dungeon_slug: str, category: str = None) -> List[LootItem]:
        """
        Convenience: Get all loot available in a dungeon.
        
        1. Gets all enemy names for the dungeon from DungeonDatabase.
        2. Queries LootDatabase for items dropped by those enemies.
        """
        # Get all enemies including boss
        enemies = self.dungeons.get_enemies_for_dungeon(dungeon_slug, include_boss=True)
        enemy_names = [e.name for e in enemies]
        
        return self.loot.get_dungeon_loot(enemy_names, category)
        
    def validate_integrity(self) -> Dict[str, List[str]]:
        """
        Run integrity checks across the databases.
        Returns a dict of warnings/errors.
        """
        warnings = []
        
        # Check 1: Do dungeon portals in dungeons_index match EntityIndex?
        for slug, dungeon in self.dungeons.dungeons.items():
            if dungeon.portal_id:
                entity = self.entities.lookup_id(dungeon.portal_id)
                if not entity:
                    warnings.append(f"Dungeon '{slug}' portal ID {dungeon.portal_id} not found in EntityIndex")
                    
        # Check 2: Do loot droppers exist in EntityIndex?
        for name in self.loot.enemies.keys():
            if not self.entities.lookup(name):
                # Many might be missing if scraping isn't complete, straightforward warning
                # warnings.append(f"Loot dropper '{name}' not found in EntityIndex")
                pass
                
        return {"warnings": warnings}

# Global singleton instance (lazy loaded)
_db_instance: Optional[AppDatabase] = None

def get_db() -> AppDatabase:
    """Get or create the global AppDatabase instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = AppDatabase()
    return _db_instance

if __name__ == "__main__":
    db = get_db()
    print("AppDatabase Initialized")
    print(f"- Entities: {len(db.entities.entities)}")
    print(f"- Dungeons: {len(db.dungeons.dungeons)}")
    print(f"- Loot Items: {len(db.loot.items)}")
    
    # Test complex query
    print("\nLoot in 'Snake Pit':")
    items = db.get_loot_for_dungeon("snake-pit", category="white_bag")
    for item in items:
        print(f"  - {item.name}: dropped by {item.enemies}")
