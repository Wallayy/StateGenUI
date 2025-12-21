"""
Dungeon Farmer Generator
Generates dungeon farming workflow using dungeon database.

Workflow:
1. In Realm: Find enemy that drops dungeon portal -> Kill -> Enter portal
2. In Dungeon: Clear specific enemies -> Kill boss -> Exit (or loop)

Usage:
    from xinjector_stategen.generators.dungeon_farmer import DungeonFarmerConfig, generate_dungeon_farmer

    # Using dungeon slug (loads data from database)
    config = DungeonFarmerConfig(
        dungeon_slug="pirate-cave",
        # Optionally override which enemies to clear in dungeon
        dungeon_clear_enemies=["Cave Pirate Veteran", "Pirate Admiral"],
    )
    generate_dungeon_farmer(config, "pirate_cave_farmer.json")
"""
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple, Optional, Union

from xinjector_stategen.workflow_builder import WorkflowBuilder

# Paths
DATA_DIR = Path(__file__).parent.parent.parent / "database" / "data"

# Entity lookup (from canonical sources)
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from database.entity_index import EntityIndex
    _ENTITY_INDEX = EntityIndex()
except ImportError:
    _ENTITY_INDEX = None


def _resolve_entity_id(name: str) -> Optional[int]:
    """Resolve entity name to ID using entity index."""
    if _ENTITY_INDEX is None:
        return None
    entity = _ENTITY_INDEX.lookup(name)
    if entity:
        return entity.id
    # Try search if exact match fails
    results = _ENTITY_INDEX.search(name, limit=1)
    if results:
        return results[0].id
    return None


def _load_dungeon_data(slug: str) -> dict:
    """Load dungeon data from database."""
    index_file = DATA_DIR / "dungeons_index.json"
    if not index_file.exists():
        raise FileNotFoundError(f"Dungeon index not found: {index_file}")

    with open(index_file, 'r', encoding='utf-8') as f:
        dungeons = json.load(f)

    if slug not in dungeons:
        raise ValueError(f"Dungeon '{slug}' not found in database. Available: {list(dungeons.keys())[:10]}...")

    return dungeons[slug]


@dataclass
class DungeonFarmerConfig:
    """Configuration for dungeon farming workflow.

    Loads dungeon data automatically from database based on slug.
    Entity names are resolved to IDs via realm.wiki lookup.
    """

    # Required: dungeon identifier
    dungeon_slug: str

    # Output name (defaults to dungeon slug)
    name: Optional[str] = None

    # Realm phase config (auto-populated from database if not specified)
    realm_map_name: str = "Realm of the Mad God"
    portal_dropper_id: Optional[int] = None  # Enemy that drops portal (auto from database)
    portal_dropper_biome: Optional[str] = None  # Which biome to search in
    portal_id: Optional[int] = None  # Portal entity ID

    # Dungeon phase config
    dungeon_map_name: Optional[str] = None  # Auto from dungeon name
    dungeon_clear_enemies: List[Union[int, str]] = field(default_factory=list)  # Specific enemies to clear
    dungeon_clear_all: bool = False  # If True, uses all enemies from database
    boss_id: Optional[int] = None  # Auto from database

    # Patrol waypoints (for realm and dungeon)
    realm_patrol_waypoints: List[Tuple[float, float]] = field(default_factory=list)
    dungeon_patrol_waypoints: List[Tuple[float, float]] = field(default_factory=list)

    # Behavior
    exit_after_boss: bool = True  # Exit dungeon after killing boss
    loop: bool = True  # Loop back to realm phase after dungeon

    def __post_init__(self):
        """Load dungeon data and resolve IDs."""
        # Load dungeon data
        dungeon_data = _load_dungeon_data(self.dungeon_slug)

        # Set name
        if self.name is None:
            self.name = self.dungeon_slug.replace('-', '_')

        # Set dungeon map name
        if self.dungeon_map_name is None:
            self.dungeon_map_name = dungeon_data.get('name', self.dungeon_slug)

        # Get portal dropper from database
        if self.portal_dropper_id is None:
            droppers = dungeon_data.get('portal_dropped_by', [])
            if droppers:
                # Use first dropper with an ID
                for dropper in droppers:
                    if dropper.get('id'):
                        self.portal_dropper_id = dropper['id']
                        self.portal_dropper_biome = dropper.get('biome')
                        break

        # Get boss ID
        if self.boss_id is None:
            boss = dungeon_data.get('boss')
            if boss:
                boss_name = boss.get('name')
                if boss_name:
                    self.boss_id = _resolve_entity_id(boss_name)

        # Get dungeon enemies
        if self.dungeon_clear_all and not self.dungeon_clear_enemies:
            enemies = dungeon_data.get('enemies', [])
            for enemy in enemies:
                enemy_name = enemy.get('name')
                if enemy_name:
                    enemy_id = _resolve_entity_id(enemy_name)
                    if enemy_id:
                        self.dungeon_clear_enemies.append(enemy_id)
        elif self.dungeon_clear_enemies:
            # Resolve any string names to IDs
            resolved = []
            for enemy in self.dungeon_clear_enemies:
                if isinstance(enemy, str):
                    enemy_id = _resolve_entity_id(enemy)
                    if enemy_id:
                        resolved.append(enemy_id)
                else:
                    resolved.append(enemy)
            self.dungeon_clear_enemies = resolved

        # Store raw dungeon data for reference
        self._dungeon_data = dungeon_data


def generate_dungeon_farmer(config: DungeonFarmerConfig, output_path: Optional[str] = None) -> str:
    """
    Generate a dungeon farming workflow from config.

    Args:
        config: DungeonFarmerConfig with dungeon parameters
        output_path: Optional output file path

    Returns:
        Path to generated file
    """
    b = WorkflowBuilder()
    gen = b.gen  # Access underlying StateGenerator for low-level nodes

    # State names
    realm_state = f"{config.name}_realm"
    dungeon_state = f"{config.name}_dungeon"

    # =========================================================================
    # REALM PHASE: Find portal dropper -> Kill -> Enter portal
    # =========================================================================

    # Map trigger for Realm
    map_realm = b.create_map_trigger(config.realm_map_name, (0, 0))

    # If we have a portal dropper, create find/kill/enter sequence
    if config.portal_dropper_id:
        # Create find target pattern for portal dropper
        dropper_find = b.create_find_target(
            [config.portal_dropper_id],
            (-200, 0),
            object_type=0  # Enemy type
        )

        # Move to dropper
        move_to_dropper = b.create_move_to_target((-600, 0), offset_dist=2.5)

        # After killing dropper, look for portal
        portal_find = b.create_find_target(
            [config.portal_id] if config.portal_id else [1815],  # Default realm portal
            (-800, 0),
            object_type=1  # Portal type
        )

        # Move to portal
        move_to_portal = b.create_move_to_target((-1200, 0))

        # Enter portal
        enter_portal = b.create_portal_entry((-1400, 0))

        # Links - Realm map -> Find dropper -> Move to dropper
        b.link_exec(map_realm, "In", dropper_find["check"], "Out")
        b.link_exec(dropper_find["check"], "True", move_to_dropper["move"], "Out")
        b.link_data(dropper_find["finder"], "Pos", move_to_dropper["offset"], "Pos")

        # After moving to dropper -> Find portal -> Move to portal -> Enter
        b.link_exec(move_to_dropper["move"], "In", portal_find["check"], "Out")
        b.link_exec(portal_find["check"], "True", move_to_portal["move"], "Out")
        b.link_data(portal_find["finder"], "Pos", move_to_portal["move"], "Position")
        b.link_exec(move_to_portal["move"], "In", enter_portal["portal"], "Out")
        b.link_data(portal_find["finder"], "ID", enter_portal["portal"], "Portal ID")

    # =========================================================================
    # DUNGEON PHASE: Clear enemies -> Kill boss -> Exit
    # =========================================================================

    # Map trigger for dungeon
    map_dungeon = b.create_map_trigger(config.dungeon_map_name, (0, 600))

    # Create enemy list for dungeon enemies (including boss)
    all_dungeon_enemies = list(config.dungeon_clear_enemies)
    if config.boss_id and config.boss_id not in all_dungeon_enemies:
        all_dungeon_enemies.append(config.boss_id)

    if all_dungeon_enemies:
        # Find dungeon enemies
        dungeon_find = b.create_find_target(
            all_dungeon_enemies,
            (-200, 600),
            object_type=0
        )

        # Move to nearest enemy
        move_to_enemy = b.create_move_to_target((-600, 600), offset_dist=2.5)

        # Links - Dungeon map -> Find enemies -> Move to enemy
        b.link_exec(map_dungeon, "In", dungeon_find["check"], "Out")
        b.link_exec(dungeon_find["check"], "True", move_to_enemy["move"], "Out")
        b.link_data(dungeon_find["finder"], "Pos", move_to_enemy["offset"], "Pos")

        # Loop back - REMOVED for DAG
        # b.link_exec(move_to_enemy["move"], "In", dungeon_find["check"], "Out")

    # =========================================================================
    # OUTPUT
    # =========================================================================
    if output_path is None:
        output_dir = Path(__file__).parent.parent.parent / "generated"
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f"{config.name}_farmer.json")

    b.save(output_path)
    return output_path


def print_dungeon_info(slug: str):
    """Print information about a dungeon from the database."""
    data = _load_dungeon_data(slug)

    print(f"\n{'='*60}")
    print(f"Dungeon: {data.get('name')} ({slug})")
    print(f"{'='*60}")
    print(f"Difficulty: {data.get('difficulty')}")

    # Boss
    boss = data.get('boss')
    if boss:
        boss_id = _resolve_entity_id(boss['name']) if boss.get('name') else None
        print(f"\nBoss: {boss.get('name')} (id: {boss_id})")

    # Portal droppers
    droppers = data.get('portal_dropped_by', [])
    if droppers:
        print(f"\nPortal dropped by ({len(droppers)}):")
        for d in droppers[:5]:
            print(f"  - {d['name']} (id: {d.get('id')}) in {d.get('biome')}")

    # Enemies
    enemies = data.get('enemies', [])
    if enemies:
        print(f"\nDungeon enemies ({len(enemies)}):")
        for e in enemies[:10]:
            enemy_id = _resolve_entity_id(e['name']) if e.get('name') else None
            print(f"  - {e['name']} (id: {enemy_id})")
        if len(enemies) > 10:
            print(f"  ... and {len(enemies) - 10} more")


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        slug = sys.argv[1]
        print_dungeon_info(slug)

        # Generate example
        print("\nGenerating farmer state...")
        config = DungeonFarmerConfig(
            dungeon_slug=slug,
            dungeon_clear_all=True,
        )
        output = generate_dungeon_farmer(config)
        print(f"Generated: {output}")
    else:
        print("Usage: python dungeon_farmer.py <dungeon-slug>")
        print("\nExample dungeons:")
        print("  python dungeon_farmer.py pirate-cave")
        print("  python dungeon_farmer.py sprite-world")
        print("  python dungeon_farmer.py abyss-of-demons")
