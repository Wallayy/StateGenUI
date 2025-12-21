#!/usr/bin/env python3
"""
Entity Index - Builds entity lookup from canonical sources.

Replaces realm_wiki_cache.json with dynamic loading from:
- dungeons_index.json (bosses, enemies, portals, portal droppers)
- biomes_complete.json (monsters, heroes, encounters, beacon guardians)

Usage:
    from database.entity_index import EntityIndex
    index = EntityIndex()
    entity = index.lookup("Sprite God")
    results = index.search("sprite")
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set

# Paths to canonical sources
_DATABASE_DIR = Path(__file__).parent
_DATA_DIR = _DATABASE_DIR / "data"
_DUNGEONS_FILE = _DATA_DIR / "dungeons_index.json"
_BIOMES_FILE = _DATA_DIR / "biomes_complete.json"


@dataclass
class Entity:
    """Represents a game entity with rich metadata."""
    name: str
    id: int
    entity_type: str  # 'enemy', 'boss', 'portal', 'beacon_guardian', 'hero', 'encounter'

    # Optional metadata
    dungeon: Optional[str] = None       # Which dungeon this belongs to
    biome: Optional[str] = None         # Which biome this belongs to
    category: Optional[str] = None      # Sub-category (e.g., 'treasure_room_boss')
    drops_dungeon: Optional[str] = None # Dungeon portal this enemy drops
    drops_guaranteed: bool = False      # If dungeon drop is guaranteed
    white_bag_drops: List[str] = field(default_factory=list)
    wiki_url: Optional[str] = None

    @property
    def obj_type(self) -> str:
        """Compatibility with RealmWikiLookup Entity."""
        return self.entity_type

    @property
    def url(self) -> str:
        """Compatibility with RealmWikiLookup Entity."""
        if self.wiki_url:
            if self.wiki_url.startswith('/'):
                return f"https://www.realmeye.com{self.wiki_url}"
            return self.wiki_url
        return f"https://www.realmeye.com/wiki/{self.name.lower().replace(' ', '-')}"


class EntityIndex:
    """
    Entity lookup built from canonical sources (dungeons_index.json, biomes_complete.json).

    Provides fast lookup by name or ID, and fuzzy search.
    """

    def __init__(self,
                 dungeons_file: Path = _DUNGEONS_FILE,
                 biomes_file: Path = _BIOMES_FILE):
        self.dungeons_file = dungeons_file
        self.biomes_file = biomes_file

        # Primary indexes
        self.entities: Dict[str, Entity] = {}  # name_lower -> Entity
        self.id_map: Dict[int, Entity] = {}    # id -> Entity

        # Additional indexes for rich queries
        self.by_dungeon: Dict[str, List[Entity]] = {}  # dungeon_name -> entities
        self.by_biome: Dict[str, List[Entity]] = {}    # biome_name -> entities
        self.portals: Dict[str, Entity] = {}           # dungeon_name -> portal entity
        self.bosses: Dict[str, Entity] = {}            # dungeon_name -> boss entity

        # Track what we've loaded
        self._loaded_dungeons = False
        self._loaded_biomes = False

        self._load_all()

    def _add_entity(self, entity: Entity):
        """Add entity to all indexes."""
        name_lower = entity.name.lower()

        # Avoid duplicates - prefer more specific entity
        if name_lower in self.entities:
            existing = self.entities[name_lower]
            # Keep the one with more metadata
            if existing.dungeon and not entity.dungeon:
                return
            if existing.biome and not entity.biome:
                return

        self.entities[name_lower] = entity
        self.id_map[entity.id] = entity

        # Add to secondary indexes
        if entity.dungeon:
            if entity.dungeon not in self.by_dungeon:
                self.by_dungeon[entity.dungeon] = []
            self.by_dungeon[entity.dungeon].append(entity)

        if entity.biome:
            if entity.biome not in self.by_biome:
                self.by_biome[entity.biome] = []
            self.by_biome[entity.biome].append(entity)

    def _load_all(self):
        """Load all canonical sources."""
        self._load_dungeons()
        self._load_biomes()

    def _load_dungeons(self):
        """Load entities from dungeons_index.json."""
        if not self.dungeons_file.exists():
            print(f"[WARN] Dungeons file not found: {self.dungeons_file}")
            return

        try:
            with open(self.dungeons_file, 'r', encoding='utf-8') as f:
                dungeons = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load dungeons: {e}")
            return

        for dungeon_slug, dungeon in dungeons.items():
            dungeon_name = dungeon.get('name', dungeon_slug)

            # 1. Portal (dungeon entry portal)
            portal_id = dungeon.get('portal_id')
            if portal_id:
                portal_name = f"{dungeon_name} Portal"
                portal = Entity(
                    name=portal_name,
                    id=portal_id,
                    entity_type='portal',
                    dungeon=dungeon_name,
                    wiki_url=dungeon.get('wiki_url')
                )
                self._add_entity(portal)
                self.portals[dungeon_name] = portal

            # 2. Boss
            boss_data = dungeon.get('boss')
            if boss_data and boss_data.get('id'):
                boss = Entity(
                    name=boss_data['name'],
                    id=boss_data['id'],
                    entity_type='boss',
                    dungeon=dungeon_name,
                    white_bag_drops=dungeon.get('white_bag_drops', []),
                    wiki_url=boss_data.get('wiki_url')
                )
                self._add_entity(boss)
                self.bosses[dungeon_name] = boss

            # 3. Enemies
            for enemy in dungeon.get('enemies', []):
                if not enemy.get('id'):
                    continue

                category = enemy.get('category', 'enemy')
                entity = Entity(
                    name=enemy['name'],
                    id=enemy['id'],
                    entity_type='enemy' if category == 'enemy' else category,
                    dungeon=dungeon_name,
                    category=category,
                    wiki_url=enemy.get('wiki_url')
                )
                self._add_entity(entity)

            # 4. Portal droppers (realm enemies that drop this dungeon's portal)
            for dropper in dungeon.get('portal_dropped_by', []):
                if not dropper.get('id'):
                    continue

                # These are biome enemies, so check if already exists
                name_lower = dropper['name'].lower()
                if name_lower in self.entities:
                    # Update existing with drop info
                    existing = self.entities[name_lower]
                    if not existing.drops_dungeon:
                        existing.drops_dungeon = dungeon_name
                        existing.drops_guaranteed = dropper.get('guaranteed', False)
                else:
                    entity = Entity(
                        name=dropper['name'],
                        id=dropper['id'],
                        entity_type='enemy',
                        biome=dropper.get('biome'),
                        drops_dungeon=dungeon_name,
                        drops_guaranteed=dropper.get('guaranteed', False)
                    )
                    self._add_entity(entity)

        self._loaded_dungeons = True

    def _load_biomes(self):
        """Load entities from biomes_complete.json."""
        if not self.biomes_file.exists():
            print(f"[WARN] Biomes file not found: {self.biomes_file}")
            return

        try:
            with open(self.biomes_file, 'r', encoding='utf-8') as f:
                biomes = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load biomes: {e}")
            return

        for biome_slug, biome in biomes.items():
            # Skip metadata
            if biome_slug.startswith('_') or not isinstance(biome, dict):
                continue

            biome_name = biome.get('name', biome_slug)

            # 1. Monsters (regular biome enemies)
            for monster in biome.get('monsters', []):
                if not monster.get('id'):
                    continue

                # Check if already exists (from dungeon portal_dropped_by)
                name_lower = monster['name'].lower()
                if name_lower in self.entities:
                    existing = self.entities[name_lower]
                    # Update biome if not set
                    if not existing.biome:
                        existing.biome = biome_name
                    continue

                entity = Entity(
                    name=monster['name'],
                    id=monster['id'],
                    entity_type='enemy',
                    biome=biome_name,
                    drops_dungeon=monster.get('drops_dungeon'),
                    drops_guaranteed=monster.get('guaranteed', False),
                    wiki_url=monster.get('wiki_url')
                )
                self._add_entity(entity)

            # 2. Heroes (quest enemies)
            for hero in biome.get('heroes', []):
                if not hero.get('id'):
                    continue

                entity = Entity(
                    name=hero['name'],
                    id=hero['id'],
                    entity_type='hero',
                    biome=biome_name,
                    drops_dungeon=hero.get('drops_dungeon'),
                    drops_guaranteed=hero.get('guaranteed', False),
                    wiki_url=hero.get('wiki_url')
                )
                self._add_entity(entity)

            # 3. Encounters (event bosses)
            for encounter in biome.get('encounters', []):
                if not encounter.get('id'):
                    continue

                entity = Entity(
                    name=encounter['name'],
                    id=encounter['id'],
                    entity_type='encounter',
                    biome=biome_name,
                    drops_dungeon=encounter.get('drops_dungeon'),
                    drops_guaranteed=encounter.get('guaranteed', False),
                    wiki_url=encounter.get('wiki_url')
                )
                self._add_entity(entity)

            # 4. Beacon Guardian
            guardian = biome.get('beacon_guardian')
            if guardian and guardian.get('id'):
                entity = Entity(
                    name=guardian['name'],
                    id=guardian['id'],
                    entity_type='beacon_guardian',
                    biome=biome_name,
                    wiki_url=guardian.get('wiki_url')
                )
                self._add_entity(entity)

        self._loaded_biomes = True

    def lookup(self, name: str) -> Optional[Entity]:
        """
        Look up entity by exact name (case-insensitive).

        Args:
            name: Entity name to look up

        Returns:
            Entity if found, None otherwise
        """
        return self.entities.get(name.lower())

    def lookup_id(self, entity_id: int) -> Optional[Entity]:
        """
        Look up entity by ID.

        Args:
            entity_id: Entity ID to look up

        Returns:
            Entity if found, None otherwise
        """
        return self.id_map.get(entity_id)

    def search(self, query: str, limit: int = 20,
               entity_types: Optional[Set[str]] = None) -> List[Entity]:
        """
        Fuzzy search for entities.

        Args:
            query: Search query (case-insensitive, partial match)
            limit: Maximum results to return
            entity_types: Optional filter by entity types

        Returns:
            List of matching entities, sorted by relevance
        """
        query_lower = query.lower()
        results = []

        # Exact match first
        exact = self.entities.get(query_lower)
        if exact:
            if not entity_types or exact.entity_type in entity_types:
                results.append(exact)

        # Starts-with matches (higher priority)
        for name, entity in self.entities.items():
            if entity in results:
                continue
            if entity_types and entity.entity_type not in entity_types:
                continue
            if name.startswith(query_lower):
                results.append(entity)
                if len(results) >= limit:
                    break

        # Contains matches
        if len(results) < limit:
            for name, entity in self.entities.items():
                if entity in results:
                    continue
                if entity_types and entity.entity_type not in entity_types:
                    continue
                if query_lower in name:
                    results.append(entity)
                    if len(results) >= limit:
                        break

        return results

    def get_id(self, name: str) -> Optional[int]:
        """
        Get entity ID by name.

        Args:
            name: Entity name

        Returns:
            Entity ID if found, None otherwise
        """
        entity = self.lookup(name)
        return entity.id if entity else None

    def get_dungeon_portal(self, dungeon_name: str) -> Optional[Entity]:
        """Get the portal entity for a dungeon."""
        return self.portals.get(dungeon_name)

    def get_dungeon_boss(self, dungeon_name: str) -> Optional[Entity]:
        """Get the boss entity for a dungeon."""
        return self.bosses.get(dungeon_name)

    def get_dungeon_entities(self, dungeon_name: str) -> List[Entity]:
        """Get all entities belonging to a dungeon."""
        return self.by_dungeon.get(dungeon_name, [])

    def get_biome_entities(self, biome_name: str) -> List[Entity]:
        """Get all entities belonging to a biome."""
        return self.by_biome.get(biome_name, [])

    def stats(self) -> Dict:
        """Get statistics about loaded entities."""
        type_counts = {}
        for entity in self.entities.values():
            t = entity.entity_type
            type_counts[t] = type_counts.get(t, 0) + 1

        return {
            'total': len(self.entities),
            'by_type': type_counts,
            'dungeons_with_portals': len(self.portals),
            'dungeons_with_bosses': len(self.bosses),
            'biomes': len(self.by_biome),
        }


# Convenience function for quick lookups
_default_index: Optional[EntityIndex] = None

def get_index() -> EntityIndex:
    """Get or create the default EntityIndex instance."""
    global _default_index
    if _default_index is None:
        _default_index = EntityIndex()
    return _default_index


if __name__ == "__main__":
    # Quick test
    index = EntityIndex()
    stats = index.stats()
    print(f"Loaded {stats['total']} entities")
    print(f"By type: {stats['by_type']}")
    print(f"Dungeons with portals: {stats['dungeons_with_portals']}")
    print(f"Dungeons with bosses: {stats['dungeons_with_bosses']}")

    # Test search
    print("\nSearch 'sprite':")
    for e in index.search("sprite", limit=5):
        print(f"  {e.name} ({e.id}) - {e.entity_type}")

    # Test portal lookup
    print("\nSprite World Portal:")
    portal = index.get_dungeon_portal("Sprite World")
    if portal:
        print(f"  {portal.name} ({portal.id})")
