"""
Realm Farmer Generator
Generates beacon search + clear mobs workflow for any biome

Supports entity name resolution via realm.wiki lookup.

Usage:
    from xinjector_stategen.generators.realm_farmer import RealmFarmerConfig, generate_realm_farmer

    # Using numeric IDs
    config = RealmFarmerConfig(
        name="sprite_world",
        map_name="Realm of the Mad God",
        beacon_enemy_id=53009,
        beacon_position=(1246.81, 532.26),
        clear_enemy_ids=[9828],
        portal_id=14861,
        patrol_waypoints=[...],
    )

    # Or using string names (resolved automatically)
    config = RealmFarmerConfig(
        name="sprite_world",
        beacon_enemy_id="Captured Sprite Beacon",
        clear_enemy_ids=["Sprite God"],
        portal_id="Sprite World",
        ...
    )
    generate_realm_farmer(config, "output.json")
"""
import os
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Union

from xinjector_stategen.workflow_builder import WorkflowBuilder

# Import entity database for name resolution
try:
    from xinjector_stategen.entities import EntityDatabase
    _ENTITY_DB = EntityDatabase()
except ImportError:
    _ENTITY_DB = None


def _resolve_id(entity: Union[int, str, None]) -> Optional[int]:
    """Resolve entity name to ID."""
    if entity is None:
        return None
    if isinstance(entity, int):
        return entity
    if _ENTITY_DB is None:
        raise ValueError(f"Cannot resolve '{entity}': EntityDatabase not available")
    resolved = _ENTITY_DB.resolve_entity(entity)
    if resolved is None:
        raise ValueError(f"Could not resolve entity '{entity}'")
    return resolved


def _resolve_ids(entities: List[Union[int, str]]) -> List[int]:
    """Resolve list of entity names/IDs to IDs."""
    return [_resolve_id(e) for e in entities]


@dataclass
class RealmFarmerConfig:
    """Configuration for realm farming workflow

    Entity IDs can be specified as integers or string names.
    String names are automatically resolved via realm.wiki lookup.
    """

    # Basic info
    name: str  # Used for output filename and state naming
    map_name: str = "Realm of the Mad God"

    # Beacon search config
    beacon_enemy_id: Union[int, str] = 0  # Enemy ID/name at beacon location
    beacon_position: Tuple[float, float] = (0, 0)  # Beacon center coords
    beacon_distance_threshold: float = 10.0

    # Clear mobs config
    clear_enemy_ids: List[Union[int, str]] = field(default_factory=list)  # Enemies to kill
    portal_id: Optional[Union[int, str]] = None  # Portal to enter (objectType=1), or None to skip
    portal_ids: List[Union[int, str]] = field(default_factory=list)  # Alternative: multiple portals
    patrol_waypoints: List[Tuple[float, float]] = field(default_factory=list)
    enemy_offset_dist: float = 2.5

    # Optional: dungeon phase config (for after entering portal)
    dungeon_map_name: Optional[str] = None
    dungeon_boss_id: Optional[Union[int, str]] = None  # Boss ID, checked LAST
    dungeon_additional_enemies: Optional[List[Union[int, str]]] = None  # Additional enemies, checked FIRST
    dungeon_exit_portal_id: int = 1796  # Realm Portal - always the same

    def __post_init__(self):
        """Resolve string entity names to IDs."""
        if isinstance(self.beacon_enemy_id, str):
            self.beacon_enemy_id = _resolve_id(self.beacon_enemy_id)
        if self.portal_id is not None and isinstance(self.portal_id, str):
            self.portal_id = _resolve_id(self.portal_id)
        if self.clear_enemy_ids:
            self.clear_enemy_ids = _resolve_ids(self.clear_enemy_ids)
        if self.dungeon_boss_id is not None and isinstance(self.dungeon_boss_id, str):
            self.dungeon_boss_id = _resolve_id(self.dungeon_boss_id)
        if self.dungeon_additional_enemies:
            self.dungeon_additional_enemies = _resolve_ids(self.dungeon_additional_enemies)


def generate_realm_farmer(config: RealmFarmerConfig, output_path: Optional[str] = None) -> str:
    """
    Generate a realm farming workflow from config.

    Args:
        config: RealmFarmerConfig with all parameters
        output_path: Optional output file path. If None, uses default location.

    Returns:
        Path to generated file
    """
    b = WorkflowBuilder()

    # State names based on config name
    beacon_state = f"{config.name}_beacon"
    clear_state = f"{config.name}_clear"

    # =========================================================================
    # NEXUS LEAVE LOGIC (Go to Nexus -> Enter Realm)
    # =========================================================================
    # Independent event chain starting with MapChange("Nexus")
    # Finds Realm Portal (1810) and enters it
    b.create_nexus_leave(
        position=(0, -200),
        portal_id=1810  # Standard Realm Portal
    )

    # =========================================================================
    # MAP TRIGGER: Realm -> beacon search
    # =========================================================================
    map_realm = b.create_map_trigger(config.map_name, (1800, -200))
    push_beacon = b.create_push(beacon_state, (1400, -200))
    b.link_exec(map_realm, "In", push_beacon, "Out")

    # =========================================================================
    # BEACON SEARCH PHASE
    # =========================================================================
    beacon = b.create_beacon_search(
        beacon_enemy_id=config.beacon_enemy_id,
        beacon_position=config.beacon_position,
        next_state=clear_state,
        position=(1600, 0),
        distance_threshold=config.beacon_distance_threshold,
    )
    # Rename the start node to match our naming
    beacon["start"].config["nodeName"] = beacon_state

    # =========================================================================
    # CLEAR MOBS PHASE
    # =========================================================================
    clear = b.create_clear_mobs(
        enemy_ids=config.clear_enemy_ids,
        portal_id=config.portal_id,
        patrol_waypoints=config.patrol_waypoints,
        position=(1600, 600),
        enemy_offset_dist=config.enemy_offset_dist,
    )
    # Rename the start node
    clear["start"].config["nodeName"] = clear_state

    # =========================================================================
    # DUNGEON PHASE (Optional)
    # =========================================================================
    if config.dungeon_map_name and config.dungeon_boss_id:
        dungeon_state = f"{config.name}_dungeon"
        dungeon_boss = config.dungeon_boss_id
        dungeon_additional = config.dungeon_additional_enemies or []
        dungeon_portal = config.dungeon_exit_portal_id

        # Layout base position for dungeon phase
        dx, dy = 2000, 1200

        # 1. Map Trigger → Push to dungeon state
        map_dungeon = b.create_map_trigger(config.dungeon_map_name, (dx, dy))
        push_dungeon = b.create_push(dungeon_state, (dx - 200, dy))
        b.link_exec(map_dungeon, "In", push_dungeon, "Out")

        # 2. Start Node for dungeon state
        start_dungeon = b.create_start(dungeon_state, (dx, dy + 400))

        # Track the "entry point" to boss check (may come from start or additional enemies)
        boss_check_entry_node = start_dungeon
        boss_check_entry_pin = "In"

        # 3. Additional Enemies check (optional, checked FIRST)
        if dungeon_additional:
            additional_find = b.create_find_target(dungeon_additional, (dx - 200, dy + 400))
            b.link_exec(start_dungeon, "In", additional_find["check"], "Out")

            # True: Move to additional enemy → loop back
            move_to_additional = b.create_move_to_target((dx - 600, dy + 400), offset_dist=2.5)
            b.link_exec(additional_find["check"], "True", move_to_additional["move"], "Out")
            b.link_data(additional_find["finder"], "Pos", move_to_additional["offset"], "Pos")
            # b.link_exec(move_to_additional["move"], "In", additional_find["check"], "Out") # Loop - REMOVED

            # False: proceed to boss check
            boss_check_entry_node = additional_find["check"]
            boss_check_entry_pin = "False"

        # 4. Boss check (checked LAST, triggers exit when gone)
        boss_find = b.create_find_target([dungeon_boss], (dx - 200, dy + 600))
        b.link_exec(boss_check_entry_node, boss_check_entry_pin, boss_find["check"], "Out")

        # True: Move to boss
        move_to_boss = b.create_move_to_target((dx - 600, dy + 600), offset_dist=2.5)
        b.link_exec(boss_find["check"], "True", move_to_boss["move"], "Out")
        b.link_data(boss_find["finder"], "Pos", move_to_boss["offset"], "Pos") 
        # b.link_exec(move_to_boss["move"], "In", boss_find["check"], "Out") # Loop - REMOVED

        # 5. False branch (boss dead): Exit portal sequence
        if dungeon_portal:
            # Find exit portal (object_type=1 for portals)
            exit_find = b.create_find_target([dungeon_portal], (dx - 600, dy + 800), object_type=1)
            b.link_exec(boss_find["check"], "False", exit_find["check"], "Out")

            # Move to exit portal
            move_to_exit = b.create_move_to_target((dx - 1000, dy + 800))
            b.link_exec(exit_find["check"], "True", move_to_exit["move"], "Out")
            b.link_data(exit_find["finder"], "Pos", move_to_exit["move"], "Position")

            # Enter exit portal
            enter_exit = b.create_portal_entry((dx - 1200, dy + 800))
            b.link_exec(move_to_exit["move"], "In", enter_exit["portal"], "Out")
            b.link_data(exit_find["finder"], "ID", enter_exit["portal"], "Portal ID")

            # If exit portal not found, do nothing (evaluation will retry on next tick)
            # b.link_exec(exit_find["check"], "False", boss_find["check"], "Out") # Loop - REMOVED

    # =========================================================================
    # OUTPUT
    # =========================================================================
    if output_path is None:
        output_dir = os.path.join(os.path.dirname(__file__), "..", "..", "generated")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{config.name}_farmer.json")

    b.save(output_path)
    return output_path


# =============================================================================
# PRESET CONFIGURATIONS
# =============================================================================

# Example: Sprite World farming config
SPRITE_WORLD_CONFIG = RealmFarmerConfig(
    name="sprite_world",
    map_name="Realm of the Mad God",
    beacon_enemy_id=53009,
    beacon_position=(1246.81, 532.26),
    clear_enemy_ids=[9828],
    portal_id=14861,
    patrol_waypoints=[
        (1316.47, 536.50),
        (1304.53, 471.53),
        (1361.44, 422.06),
        (1457.50, 373.41),
        (1289.57, 411.23),
        (1194.76, 457.94),
        (1152.91, 535.45),
        (1179.26, 601.55),
        (1262.22, 640.79),
        (1329.77, 681.43),
        (1412.25, 673.38),
        (1438.17, 708.59),
        (1359.37, 703.51),
    ],
)


def main():
    """CLI entry point"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Generate realm farmer states")
    parser.add_argument("--config", type=str, help="Path to config JSON file")
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output path (default: ../generated/{name}_farmer.json)",
    )
    parser.add_argument("--example", action="store_true", help="Use example config")

    args = parser.parse_args()

    if args.example:
        config = SPRITE_WORLD_CONFIG
    else:
        if not args.config:
            print("Error: --config is required unless --example is used")
            return
        with open(args.config, "r") as f:
            data = json.load(f)
        config = RealmFarmerConfig(**data)

    output_path = generate_realm_farmer(config, args.output)
    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()
