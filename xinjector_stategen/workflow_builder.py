"""
Workflow Builder (formerly Modular State Builder)
High-level pattern functions for composing XINJECTOR workflows

Layout Model (Depth-Based):
- Execution flows RIGHT to LEFT (high X to low X)
- CONTINUATION branches stay at same Y level
- NESTED DECISION branches go DOWN (+Y)
- DATA NODES positioned ABOVE (-Y offset) the execution chain
- TERMINAL nodes (PushNode, EnterPortal) end the flow
"""
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
from xinjector_stategen.dag.state_generator import StateGenerator, Node


# Layout constants
H_SPACE = 200.0       # Horizontal spacing between nodes
DEPTH_SPACE = 200.0   # Y spacing between decision depths
DATA_OFFSET = -150.0  # Y offset for data nodes (above execution)


@dataclass
class PatternNodes:
    """Container for nodes created by a pattern"""
    nodes: Dict[str, Node] = field(default_factory=dict)

    def __getitem__(self, key: str) -> Node:
        return self.nodes[key]

    def __setitem__(self, key: str, node: Node):
        self.nodes[key] = node

    def __contains__(self, key: str) -> bool:
        return key in self.nodes

    def __iter__(self):
        return iter(self.nodes)


class WorkflowBuilder:
    """
    High-level builder for composing workflows from reusable patterns.
    
    Uses depth-based layout model:
    - Depth 0: Entry chain (Start, Sequence, first If)
    - Depth N: Nodes reached after N nested decisions
    - Data nodes: Positioned above their consumer (negative Y offset)
    """

    def __init__(self):
        self.gen = StateGenerator()

    # =========================================================================
    # LOW-LEVEL: Direct linking helpers
    # =========================================================================
    def link_exec(self, from_node: Node, from_pin: str, to_node: Node, to_pin: str):
        """Link execution pins. Handles the pin array conventions automatically."""
        self.gen.link_pins(from_node, from_pin, to_node, to_pin)

    def link_data(self, from_node: Node, from_pin: str, to_node: Node, to_pin: str):
        """Link data pins."""
        self.gen.link_pins(from_node, from_pin, to_node, to_pin)

    # =========================================================================
    # PATTERN: Find Target
    # =========================================================================
    def create_find_target(
        self,
        enemy_ids: List[int],
        position: Tuple[float, float],
        object_type: int = 0,
    ) -> PatternNodes:
        """
        Create enemy detection nodes.

        Returns nodes: {finder, check}
        - finder: EnemyList node with Pos, Exists, ID outputs
        - check: If node for branching on Exists
        """
        x, y = position
        result = PatternNodes()

        finder = self.gen.create_enemy_list(enemy_ids, (x, y), object_type=object_type)
        result["finder"] = finder

        check = self.gen.create_if_node((x - H_SPACE, y))
        result["check"] = check
        self.link_data(finder, "Exists", check, "Condition")

        return result

    # =========================================================================
    # PATTERN: Move To Target
    # =========================================================================
    def create_move_to_target(
        self,
        position: Tuple[float, float],
        teleport: bool = False,
        offset_dist: Optional[float] = None,
    ) -> PatternNodes:
        """
        Create movement nodes (optionally with offset).

        Returns nodes: {move} or {offset, move}
        """
        x, y = position
        result = PatternNodes()

        if offset_dist is not None:
            offset = self.gen.create_offset_pos((x, y), dist=offset_dist)
            result["offset"] = offset
            move = self.gen.create_move_to((x - H_SPACE, y), teleport=teleport)
            result["move"] = move
            self.link_data(offset, "Result", move, "Position")
        else:
            move = self.gen.create_move_to((x, y), teleport=teleport)
            result["move"] = move

        return result

    # =========================================================================
    # PATTERN: Portal Entry
    # =========================================================================
    def create_portal_entry(
        self,
        position: Tuple[float, float],
    ) -> PatternNodes:
        """
        Create portal entry node.

        Returns nodes: {portal}
        """
        x, y = position
        result = PatternNodes()

        portal = self.gen.create_enter_portal((x, y))
        result["portal"] = portal

        return result

    # =========================================================================
    # PATTERN: Distance Check
    # =========================================================================
    def create_distance_check(
        self,
        target_point: Tuple[float, float],
        position: Tuple[float, float],
        threshold: float = 10.0,
    ) -> PatternNodes:
        """
        Create distance comparison nodes.
        Data nodes positioned ABOVE the If node.

        Returns nodes: {player, target, operator, comparison, check}
        """
        x, y = position
        result = PatternNodes()

        # Data layer (above execution)
        data_y = y + DATA_OFFSET
        player = self.gen.create_player_pos((x + H_SPACE, data_y))
        result["player"] = player

        target = self.gen.create_point_list([target_point], (x, data_y))
        result["target"] = target

        operator = self.gen.create_operator((x - H_SPACE, data_y), operator_type=0)
        result["operator"] = operator
        self.link_data(player, "Pos", operator, "A")
        self.link_data(target, "Pos", operator, "B")

        comparison = self.gen.create_comparison((x - 2*H_SPACE, data_y), comparison_type=2, val_to_compare=threshold)
        result["comparison"] = comparison
        self.link_data(operator, "Distance", comparison, "A")

        # Execution layer
        check = self.gen.create_if_node((x, y))
        result["check"] = check
        self.link_data(comparison, "Result", check, "Condition")

        return result

    # =========================================================================
    # PATTERN: Patrol Route
    # =========================================================================
    def create_patrol(
        self,
        waypoints: List[Tuple[float, float]],
        position: Tuple[float, float],
        switch_distance: float = 2.0,
    ) -> PatternNodes:
        """
        Create patrol waypoint nodes.

        Returns nodes: {pointlist, move}
        """
        x, y = position
        result = PatternNodes()

        pointlist = self.gen.create_point_list(waypoints, (x, y), switch_distance=switch_distance)
        result["pointlist"] = pointlist

        move = self.gen.create_move_to((x - H_SPACE, y))
        result["move"] = move
        self.link_data(pointlist, "Pos", move, "Position")

        return result

    # =========================================================================
    # PATTERN: Wait
    # =========================================================================
    def create_wait(
        self,
        wait_ms: int,
        position: Tuple[float, float],
    ) -> PatternNodes:
        """
        Create wait node.

        Returns nodes: {wait}
        """
        result = PatternNodes()
        wait = self.gen.create_wait(wait_ms, position)
        result["wait"] = wait
        return result

    # =========================================================================
    # PATTERN: Beacon Search (Depth-Based Layout)
    # =========================================================================
    def create_beacon_search(
        self,
        beacon_enemy_id: int,
        beacon_position: Tuple[float, float],
        next_state: str,
        position: Tuple[float, float],
        distance_threshold: float = 10.0,
    ) -> PatternNodes:
        """
        Create beacon search pattern - checks if near beacon, then searches for enemy.

        Layout (Depth-Based):
          DATA (Y-150):    PlayerPos → Operator → Comparison
          DEPTH 0 (Y):     Start → Seq → If(dist<10?) ──→ False: MoveTo(teleport) [CONTINUATION]
                                              │
                                              ▼ True [NESTED]
          DATA (Y+100):                   EnemyList
          DEPTH 1 (Y+200): If(enemy?) ──→ True: MoveTo(enemy) [CONTINUATION]
                                    └──→ False: PushNode(next) [TERMINAL]

        Args:
            beacon_enemy_id: Enemy ID to search for at beacon
            beacon_position: (x, y) coordinates of beacon center
            next_state: State to push when enemy not found
            position: Visual position for rightmost node (Start)
            distance_threshold: Distance to consider "at beacon" (default 10)

        Returns nodes: {start, sequence, distance_check, enemy_check,
                       teleport_move, enemy_move, push_next,
                       player_pos, beacon_point, operator, comparison, enemy_finder}
        """
        x, y = position
        result = PatternNodes()
        
        # === DEPTH 0: Main execution chain (Y=y) ===
        start = self.gen.create_start_node(next_state.replace("_clear", "_beacon"), (x, y))
        result["start"] = start
        
        sequence = self.gen.create_sequence((x - H_SPACE, y))
        result["sequence"] = sequence
        
        distance_check = self.gen.create_if_node((x - 2*H_SPACE, y))
        result["distance_check"] = distance_check
        
        # Continuation (False = not at beacon) - SAME Y
        teleport_move = self.gen.create_move_to((x - 3*H_SPACE, y), teleport=True)
        result["teleport_move"] = teleport_move
        
        # === DATA for Depth 0 (above execution) ===
        data_y = y + DATA_OFFSET
        player_pos = self.gen.create_player_pos((x - H_SPACE, data_y))
        result["player_pos"] = player_pos
        
        beacon_point = self.gen.create_point_list([beacon_position], (x - 2*H_SPACE, data_y))
        result["beacon_point"] = beacon_point
        
        operator = self.gen.create_operator((x - 3*H_SPACE, data_y), operator_type=0)
        result["operator"] = operator
        
        comparison = self.gen.create_comparison((x - 4*H_SPACE, data_y), comparison_type=2, val_to_compare=distance_threshold)
        result["comparison"] = comparison
        
        # === DEPTH 1: Nested decision (Y+200) ===
        depth1_y = y + DEPTH_SPACE
        enemy_check = self.gen.create_if_node((x - 2*H_SPACE, depth1_y))
        result["enemy_check"] = enemy_check
        
        # Continuation at depth 1 (True = enemy found) - SAME Y
        enemy_move = self.gen.create_move_to((x - 3*H_SPACE, depth1_y))
        result["enemy_move"] = enemy_move
        
        # Terminal (False = no enemy)
        push_next = self.gen.create_push_node(next_state, (x - 3*H_SPACE, depth1_y + DEPTH_SPACE))
        result["push_next"] = push_next
        
        # === DATA for Depth 1 (between depths) ===
        enemy_data_y = y + DEPTH_SPACE/2
        enemy_finder = self.gen.create_enemy_list([beacon_enemy_id], (x - 3*H_SPACE, enemy_data_y), object_type=0)
        result["enemy_finder"] = enemy_finder
        
        # Offset for enemy move
        enemy_offset = self.gen.create_offset_pos((x - 4*H_SPACE, enemy_data_y + 50), dist=2.5)
        result["enemy_offset"] = enemy_offset

        # === DATA LINKS ===
        self.link_data(player_pos, "Pos", operator, "A")
        self.link_data(beacon_point, "Pos", operator, "B")
        self.link_data(operator, "Distance", comparison, "A")
        self.link_data(comparison, "Result", distance_check, "Condition")
        self.link_data(beacon_point, "Pos", teleport_move, "Position")
        self.link_data(enemy_finder, "Exists", enemy_check, "Condition")
        
        # Link Finder -> Offset -> Move
        self.link_data(enemy_finder, "Pos", enemy_offset, "Pos")
        self.link_data(enemy_offset, "Result", enemy_move, "Position")

        # === EXECUTION LINKS ===
        self.link_exec(start, "In", sequence, "Out")
        self.link_exec(sequence, "In", distance_check, "Out")
        self.link_exec(distance_check, "False", teleport_move, "Out")  # Continuation
        self.link_exec(distance_check, "True", enemy_check, "Out")     # Nested
        self.link_exec(enemy_check, "True", enemy_move, "Out")         # Continuation
        # self.link_exec(enemy_move, "In", distance_check, "Out")        # Loop - REMOVED for DAG
        self.link_exec(enemy_check, "False", push_next, "Out")         # Terminal

        return result

    # =========================================================================
    # PATTERN: Clear Mobs (Depth-Based Layout)
    # =========================================================================
    def create_clear_mobs(
        self,
        enemy_ids: List[int],
        portal_id: Optional[int],
        patrol_waypoints: List[Tuple[float, float]],
        position: Tuple[float, float],
        enemy_offset_dist: float = 2.5,
    ) -> PatternNodes:
        """
        Create clear mobs pattern - patrol while checking for portal/enemies.

        Layout (Depth-Based):
          DATA (Y-150):    PointList (patrol waypoints)
          DEPTH 0 (Y):     Start → MoveTo(patrol) → If(portal?) ──→ True: Move→Enter [TERMINAL]
                                                          │
                                                          ▼ False [NESTED]
          DATA (Y+100):                              EnemyList  
          DEPTH 1 (Y+200): If(enemy?) ──→ True: OffsetPos→MoveTo [CONTINUATION]
                                    └──→ False: MoveTo(patrol) [CONTINUATION]

        Args:
            enemy_ids: List of enemy IDs to kill
            portal_id: Portal ID to enter (objectType=1), or None to skip
            patrol_waypoints: List of (x, y) patrol points
            position: Visual position for Start node
            enemy_offset_dist: Distance to maintain from enemy

        Returns nodes: {start, patrol_move, patrol_points, enemy_check, enemy_finder,
                       enemy_offset, enemy_move, [portal_check, portal_finder, portal_move, portal_enter]}
        """
        x, y = position
        result = PatternNodes()
        has_portal = portal_id is not None and portal_id != 0
        
        # === DEPTH 0: Main execution ===
        start = self.gen.create_start_node("clear_mobs", (x, y))
        result["start"] = start
        
        # Patrol move at depth 0
        patrol_move = self.gen.create_move_to((x - H_SPACE, y))
        result["patrol_move"] = patrol_move
        
        # Patrol data (above)
        patrol_points = self.gen.create_point_list(patrol_waypoints, (x - H_SPACE, y + DATA_OFFSET), switch_distance=2.0)
        result["patrol_points"] = patrol_points
        self.link_data(patrol_points, "Pos", patrol_move, "Position")
        
        if has_portal:
            # Portal check at depth 0
            portal_check = self.gen.create_if_node((x - 2*H_SPACE, y))
            result["portal_check"] = portal_check
            
            # Portal data (above depth 0)
            portal_finder = self.gen.create_enemy_list([portal_id], (x - 2*H_SPACE, y + DATA_OFFSET), object_type=1)
            result["portal_finder"] = portal_finder
            self.link_data(portal_finder, "Exists", portal_check, "Condition")
            
            # Portal True branch (continuation -> terminal)
            portal_move = self.gen.create_move_to((x - 3*H_SPACE, y))
            result["portal_move"] = portal_move
            self.link_data(portal_finder, "Pos", portal_move, "Position")
            
            portal_enter = self.gen.create_enter_portal((x - 4*H_SPACE, y))
            result["portal_enter"] = portal_enter
            self.link_data(portal_finder, "ID", portal_enter, "Portal ID")
            
            self.link_exec(portal_check, "True", portal_move, "Out")
            self.link_exec(portal_move, "In", portal_enter, "Out")
            
            # Enemy depth starts at depth 1
            enemy_depth_y = y + DEPTH_SPACE
            enemy_data_y = y + DEPTH_SPACE/2
        else:
            portal_check = None
            enemy_depth_y = y + DEPTH_SPACE
            enemy_data_y = y + DEPTH_SPACE/2
        
        # === DEPTH 1: Enemy check ===
        enemy_check = self.gen.create_if_node((x - 2*H_SPACE, enemy_depth_y))
        result["enemy_check"] = enemy_check
        
        # Enemy data (between depths)
        enemy_finder = self.gen.create_enemy_list(enemy_ids, (x - 2*H_SPACE, enemy_data_y), object_type=0)
        result["enemy_finder"] = enemy_finder
        self.link_data(enemy_finder, "Exists", enemy_check, "Condition")
        
        # Enemy True: offset + move (continuation at depth 1)
        enemy_offset = self.gen.create_offset_pos((x - 3*H_SPACE, enemy_depth_y), dist=enemy_offset_dist)
        result["enemy_offset"] = enemy_offset
        self.link_data(enemy_finder, "Pos", enemy_offset, "Pos")
        
        enemy_move = self.gen.create_move_to((x - 4*H_SPACE, enemy_depth_y))
        result["enemy_move"] = enemy_move
        self.link_data(enemy_offset, "Result", enemy_move, "Position")
        
        # Enemy False: back to patrol (continuation)
        patrol_fallback = self.gen.create_move_to((x - 3*H_SPACE, enemy_depth_y + DEPTH_SPACE))
        result["patrol_fallback"] = patrol_fallback
        self.link_data(patrol_points, "Pos", patrol_fallback, "Position")

        # === EXECUTION LINKS ===
        self.link_exec(start, "In", patrol_move, "Out")
        
        if has_portal:
            self.link_exec(patrol_move, "In", portal_check, "Out")
            self.link_exec(portal_check, "False", enemy_check, "Out")  # Nested
        else:
            self.link_exec(patrol_move, "In", enemy_check, "Out")      # Nested
        
        self.link_exec(enemy_check, "True", enemy_move, "Out")         # Continuation
        # self.link_exec(enemy_move, "In", enemy_check, "Out")           # Loop back - REMOVED for DAG
        self.link_exec(enemy_check, "False", patrol_fallback, "Out")   # Continuation

        return result

    # =========================================================================
    # FLOW: Entry Points
    # =========================================================================
    def create_start(self, name: str, position: Tuple[float, float]) -> Node:
        """Create a Start entry point."""
        return self.gen.create_start_node(name, position)

    def create_map_trigger(self, map_name: str, position: Tuple[float, float]) -> Node:
        """Create a MapChange trigger."""
        return self.gen.create_map_change(map_name, position)

    def create_push(self, target_name: str, position: Tuple[float, float]) -> Node:
        """Create a PushNode to call another state."""
        return self.gen.create_push_node(target_name, position)

    def create_sequence(self, position: Tuple[float, float]) -> Node:
        """Create a Sequence node."""
        return self.gen.create_sequence(position)

    # =========================================================================
    # PATTERN: Nexus Leave (Go to Nexus -> Enter Realm)
    # =========================================================================
    def create_nexus_leave(
        self,
        position: Tuple[float, float],
        spawn_point: Tuple[float, float] = (127.0, 170.0),
        portal_id: int = 1810,
        wait_time: int = 500,
    ) -> PatternNodes:
        """
        Create Nexus leave pattern - go to Nexus and enter a Realm.

        Flow:
        MapChange("Nexus") -> Wait(500ms) -> MoveTo(spawn point)
            -> If(portal exists)
                -> True: MoveTo(portal) -> EnterPortal
                -> False: (loops/retries via base node re-execution)

        Args:
            position: Visual position for rightmost node (MapChange)
            spawn_point: (x, y) coordinates of spawn/portal area in Nexus
            portal_id: Entity ID of Realm Portal (default: 1810)
            wait_time: Wait time after map change in ms (default: 500)

        Returns nodes: {map_change, wait, spawn_point, move_to_spawn,
                       portal_detector, if_portal, move_to_portal, enter_portal}
        """
        from xinjector_stategen.patterns.nexus_leave import NexusLeavePattern

        x, y = position
        result = PatternNodes()

        pattern = NexusLeavePattern(
            self.gen,
            spawn_point=spawn_point,
            portal_id=portal_id,
            wait_time=wait_time
        )
        pattern.build(x, y)

        # Copy nodes to result
        nodes_dict = pattern.get_nodes_dict()
        for key, node in nodes_dict.items():
            result[key] = node

        return result

    # =========================================================================
    # OUTPUT
    # =========================================================================
    def generate(self) -> str:
        return self.gen.generate()

    def save(self, filename: str):
        self.gen.save(filename)
        print(f"Generated: {filename}")
        print(f"Nodes: {len(self.gen.nodes)}")
        print(f"Links: {len(self.gen.links)}")


# Backwards compatibility alias
ModularStateBuilder = WorkflowBuilder
