#!/usr/bin/env python3
"""
Dungeon Database - Lookup and filter dungeon entities.

Provides:
- Get all dungeons
- Get dungeon by slug
- Get enemies for a dungeon (with IDs)
- Get boss for a dungeon
- Filter entities by dungeon selection
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Union
from dataclasses import dataclass


DATABASE_DIR = Path(__file__).parent
DUNGEONS_FILE = DATABASE_DIR / "data" / "dungeons_index.json"


@dataclass
class Enemy:
    """Dungeon enemy with ID and category."""
    name: str
    id: Optional[int]
    wiki_url: str = ""
    category: str = "enemy"  # enemy, miniboss, treasure_room_boss

    def to_dict(self) -> dict:
        return {"name": self.name, "id": self.id, "wiki_url": self.wiki_url, "category": self.category}


@dataclass
class Boss:
    """Dungeon boss."""
    name: str
    id: int
    wiki_url: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "id": self.id, "wiki_url": self.wiki_url}


@dataclass
class PortalDropper:
    """Entity that drops this dungeon's portal."""
    name: str
    id: int
    biome: str
    guaranteed: bool

    def to_dict(self) -> dict:
        return {"name": self.name, "id": self.id, "biome": self.biome, "guaranteed": self.guaranteed}


@dataclass
class Dungeon:
    """Dungeon with boss and enemies."""
    slug: str
    name: str
    difficulty: str
    boss: Optional[Boss]
    enemies: List[Enemy]
    portal_id: Optional[int]
    portal_dropped_by: List[PortalDropper]
    wiki_url: str = ""

    @property
    def is_biome_dungeon(self) -> bool:
        """Returns True if this dungeon drops from biome enemies."""
        return len(self.portal_dropped_by) > 0

    @property
    def biomes(self) -> List[str]:
        """Get list of biomes where this dungeon can drop."""
        return list(set(p.biome for p in self.portal_dropped_by if p.biome))

    def get_all_enemy_ids(self, include_boss: bool = True) -> List[int]:
        """Get all enemy IDs for this dungeon."""
        ids = []
        if include_boss and self.boss and self.boss.id:
            ids.append(self.boss.id)
        for enemy in self.enemies:
            if enemy.id:
                ids.append(enemy.id)
        return ids

    def to_dict(self) -> dict:
        return {
            "slug": self.slug,
            "name": self.name,
            "difficulty": self.difficulty,
            "boss": self.boss.to_dict() if self.boss else None,
            "enemies": [e.to_dict() for e in self.enemies],
            "portal_id": self.portal_id,
            "portal_dropped_by": [p.to_dict() for p in self.portal_dropped_by],
            "biomes": self.biomes,
            "wiki_url": self.wiki_url,
        }


class DungeonDatabase:
    """
    Database for dungeon lookups.

    Usage:
        db = DungeonDatabase()

        # Get single dungeon
        dungeon = db.get_dungeon("pirate-cave")

        # Get enemies for dungeon (filtered)
        enemies = db.get_enemies_for_dungeon("pirate-cave")

        # Get enemies for multiple dungeons
        enemies = db.get_enemies_for_dungeons(["pirate-cave", "snake-pit"])

        # Get boss IDs for dungeons
        boss_ids = db.get_boss_ids(["pirate-cave", "snake-pit"])
    """

    def __init__(self, dungeons_file: Path = DUNGEONS_FILE):
        self.dungeons_file = dungeons_file
        self.dungeons: Dict[str, Dungeon] = {}
        self._load()

    def _load(self):
        """Load dungeons from JSON."""
        if not self.dungeons_file.exists():
            raise FileNotFoundError(f"Dungeons file not found: {self.dungeons_file}")

        with open(self.dungeons_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for slug, ddata in data.items():
            boss = None
            if ddata.get('boss'):
                boss = Boss(
                    name=ddata['boss'].get('name', ''),
                    id=ddata['boss'].get('id'),
                    wiki_url=ddata['boss'].get('wiki_url', '')
                )

            enemies = []
            for edata in ddata.get('enemies', []):
                enemies.append(Enemy(
                    name=edata.get('name', ''),
                    id=edata.get('id'),
                    wiki_url=edata.get('wiki_url', ''),
                    category=edata.get('category', 'enemy')
                ))

            portal_dropped_by = []
            for pdata in ddata.get('portal_dropped_by', []):
                if pdata.get('id') and pdata.get('biome'):
                    portal_dropped_by.append(PortalDropper(
                        name=pdata.get('name', ''),
                        id=pdata.get('id'),
                        biome=pdata.get('biome', ''),
                        guaranteed=pdata.get('guaranteed', False)
                    ))

            self.dungeons[slug] = Dungeon(
                slug=slug,
                name=ddata.get('name', slug),
                difficulty=ddata.get('difficulty', '?'),
                boss=boss,
                enemies=enemies,
                portal_id=ddata.get('portal_id'),
                portal_dropped_by=portal_dropped_by,
                wiki_url=ddata.get('wiki_url', '')
            )

    def get_dungeon(self, slug: str) -> Optional[Dungeon]:
        """Get dungeon by slug."""
        return self.dungeons.get(slug)

    def get_all_dungeons(self) -> List[Dungeon]:
        """Get all dungeons."""
        return list(self.dungeons.values())

    def get_biome_dungeons(self) -> List[Dungeon]:
        """Get only dungeons that drop from biome enemies."""
        return [d for d in self.dungeons.values() if d.is_biome_dungeon]

    def list_dungeon_slugs(self, biome_only: bool = False) -> List[str]:
        """Get list of dungeon slugs."""
        if biome_only:
            return [d.slug for d in self.get_biome_dungeons()]
        return list(self.dungeons.keys())

    def get_enemies_for_dungeon(
        self,
        slug: str,
        include_boss: bool = True,
        category: str = None
    ) -> List[Enemy]:
        """
        Get enemies for a dungeon.

        Args:
            slug: Dungeon slug
            include_boss: Include main boss in list
            category: Filter by category (enemy, miniboss, treasure_room_boss, or None for all)
        """
        dungeon = self.get_dungeon(slug)
        if not dungeon:
            return []

        enemies = list(dungeon.enemies)
        if include_boss and dungeon.boss:
            # Boss as Enemy for unified list
            enemies.insert(0, Enemy(
                name=dungeon.boss.name,
                id=dungeon.boss.id,
                wiki_url=dungeon.boss.wiki_url,
                category='boss'
            ))

        # Filter by category if specified
        if category:
            enemies = [e for e in enemies if e.category == category]

        return enemies

    def get_special_enemies(self, slug: str) -> List[Enemy]:
        """Get minibosses and treasure room bosses for a dungeon."""
        dungeon = self.get_dungeon(slug)
        if not dungeon:
            return []

        return [e for e in dungeon.enemies if e.category in ('miniboss', 'treasure_room_boss')]

    def get_enemies_for_dungeons(
        self,
        slugs: List[str],
        include_boss: bool = True
    ) -> List[Enemy]:
        """Get all enemies for multiple dungeons (deduplicated)."""
        seen_ids = set()
        enemies = []

        for slug in slugs:
            for enemy in self.get_enemies_for_dungeon(slug, include_boss):
                if enemy.id and enemy.id not in seen_ids:
                    seen_ids.add(enemy.id)
                    enemies.append(enemy)
                elif not enemy.id:
                    # Include enemies without IDs (won't dedupe)
                    enemies.append(enemy)

        return enemies

    def get_boss_ids(self, slugs: Union[str, List[str]]) -> List[int]:
        """Get boss IDs for dungeon(s)."""
        if isinstance(slugs, str):
            slugs = [slugs]

        boss_ids = []
        for slug in slugs:
            dungeon = self.get_dungeon(slug)
            if dungeon and dungeon.boss and dungeon.boss.id:
                boss_ids.append(dungeon.boss.id)

        return boss_ids

    def get_enemy_ids(
        self,
        slugs: Union[str, List[str]],
        include_boss: bool = True
    ) -> List[int]:
        """Get all enemy IDs for dungeon(s)."""
        if isinstance(slugs, str):
            slugs = [slugs]

        ids = []
        seen = set()

        for slug in slugs:
            dungeon = self.get_dungeon(slug)
            if not dungeon:
                continue

            for eid in dungeon.get_all_enemy_ids(include_boss):
                if eid not in seen:
                    seen.add(eid)
                    ids.append(eid)

        return ids

    def search_dungeons(self, query: str) -> List[Dungeon]:
        """Search dungeons by name (case-insensitive partial match)."""
        query_lower = query.lower()
        return [
            d for d in self.dungeons.values()
            if query_lower in d.name.lower() or query_lower in d.slug.lower()
        ]


def main():
    """Test the database."""
    db = DungeonDatabase()

    print(f"Loaded {len(db.dungeons)} dungeons")
    print()

    # Test single dungeon
    dungeon = db.get_dungeon("pirate-cave")
    if dungeon:
        print(f"Dungeon: {dungeon.name}")
        print(f"  Boss: {dungeon.boss.name} (ID: {dungeon.boss.id})" if dungeon.boss else "  Boss: None")
        print(f"  Enemies: {len(dungeon.enemies)}")
        print(f"  All IDs: {dungeon.get_all_enemy_ids()}")
        print()

    # Test multi-dungeon
    test_slugs = ["pirate-cave", "snake-pit"]
    print(f"Boss IDs for {test_slugs}: {db.get_boss_ids(test_slugs)}")
    print(f"All enemy IDs: {db.get_enemy_ids(test_slugs)}")
    print()

    # Test filtering
    enemies = db.get_enemies_for_dungeons(test_slugs)
    print(f"Enemies for {test_slugs}:")
    for e in enemies[:5]:
        print(f"  {e.name}: {e.id}")
    if len(enemies) > 5:
        print(f"  ... and {len(enemies) - 5} more")


if __name__ == "__main__":
    main()
