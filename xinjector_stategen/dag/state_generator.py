"""
XINJECTOR State Script Generator
A Python-based DAG workflow generator for game automation scripts
"""

import json
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

# Base ID for generating unique pin IDs
BASE_ID = 50000

class PinType(Enum):
    """Pin data types in the system"""
    EXECUTION = "execution"
    VECTOR2 = "Vector2"
    BOOLEAN = "bool"
    FLOAT = "float"

class NodeType(Enum):
    """Available node types matching JSON strings"""
    START = "Start"
    SEQUENCE = "Sequence"
    IF = "If"
    PUSH_NODE = "PushNode"
    WAIT = "Wait"
    ENEMY_LIST = "EnemyList"
    PLAYER_POS = "PlayerPos"
    POINT = "Point"
    POINT_LIST = "PointList"
    MOVE_TO = "MoveTo"
    ENTER_PORTAL = "EnterPortal"
    MAP_CHANGE = "MapChange"
    OPERATOR = "Operator"
    COMPARISON = "Comparison"
    SAVE_POS = "SavePos"
    USE_ITEM = "UseItem"
    SEND_MESSAGE = "SendMessageL" 
    RECEIVE_MESSAGE = "ReceivedMessage"
    GROUP = "Group"
    HOTKEY = "Hotkey"
    PLAYER_COUNT = "PlayerCount"
    STATUS_LEVEL = "StatusLevel"
    SWITCH_SERVER = "SwitchServer"
    CONNECT_TO_QUEST = "ConnectToQuest"
    NEXUS = "Nexus"
    RESET_TILE_CACHE = "ResetTileCache"
    OFFSET_POS = "OffsetPos"

@dataclass
class Pin:
    """Represents a node pin (input or output)"""
    id: int
    name: str
    pin_type: PinType = PinType.EXECUTION

    def to_dict(self) -> Dict:
        return {"id": self.id, "name": self.name}

@dataclass
class Node:
    """Base class for all nodes"""
    node_type: str
    position: Tuple[float, float]
    in_pins: List[Pin] = field(default_factory=list)
    out_pins: List[Pin] = field(default_factory=list)
    config: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        result = {
            "nodeType": self.node_type,
            "position": {"x": float(self.position[0]), "y": float(self.position[1])}
        }

        if self.in_pins:
            result["inPins"] = [pin.to_dict() for pin in self.in_pins]
        if self.out_pins:
            result["outPins"] = [pin.to_dict() for pin in self.out_pins]

        # Add node-specific configuration
        result.update(self.config)

        return result

@dataclass
class Link:
    """Represents a connection between two pins"""
    left_pin_id: int  # Source (output) pin
    right_pin_id: int  # Target (input) pin

    def to_dict(self) -> Dict:
        return {
            "leftPinID": self.left_pin_id,
            "rightPinID": self.right_pin_id
        }

class StateGenerator:
    """Generate XINJECTOR state scripts programmatically"""

    def __init__(self):
        self.nodes: List[Node] = []
        self.links: List[Link] = []
        self.current_id = BASE_ID

    def get_next_id(self) -> int:
        """Generate next unique ID"""
        self.current_id += 1
        return self.current_id

    def _create_pin(self, name: str, pin_type: PinType = PinType.EXECUTION) -> Pin:
        return Pin(self.get_next_id(), name, pin_type)

    def create_start_node(self, name: str, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.START.value, position, in_pins=[self._create_pin("In")], config={"nodeName": name})
        self.nodes.append(node)
        return node

    def create_sequence(self, position: Tuple[float, float]) -> Node:
        # Sequence typically has 5 inputs (In, In 2..5) and 1 Out
        inputs = [self._create_pin("In")] + [self._create_pin(f"In {i}") for i in range(2, 6)]
        node = Node(NodeType.SEQUENCE.value, position, in_pins=inputs, out_pins=[self._create_pin("Out")])
        self.nodes.append(node)
        return node

    def create_if_node(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.IF.value, position, 
                   in_pins=[self._create_pin("True"), self._create_pin("False"), self._create_pin("Condition", PinType.BOOLEAN)],
                   out_pins=[self._create_pin("Out")])
        self.nodes.append(node)
        return node

    def create_push_node(self, target_state: str, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.PUSH_NODE.value, position, out_pins=[self._create_pin("Out")], config={"name": target_state})
        self.nodes.append(node)
        return node

    def create_wait(self, wait_time: int, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.WAIT.value, position, in_pins=[self._create_pin("In")], out_pins=[self._create_pin("Out")], config={"waitTime": wait_time})
        self.nodes.append(node)
        return node

    def create_enemy_list(self, enemy_ids: List[int], position: Tuple[float, float], object_type: int = 0, sort_type: int = 0, ignore_invul: bool = False) -> Node:
        node = Node(NodeType.ENEMY_LIST.value, position, 
                   out_pins=[self._create_pin("Pos", PinType.VECTOR2), self._create_pin("Exists", PinType.BOOLEAN), self._create_pin("ID", PinType.FLOAT)],
                   config={"enemyList": enemy_ids, "objectType": object_type, "sortType": sort_type, "ignoreInvul": ignore_invul})
        self.nodes.append(node)
        return node

    def create_player_pos(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.PLAYER_POS.value, position, out_pins=[self._create_pin("Pos", PinType.VECTOR2)])
        self.nodes.append(node)
        return node

    def create_point(self, x: float, y: float, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.POINT.value, position, out_pins=[self._create_pin("Pos", PinType.VECTOR2)], config={"point": {"x": x, "y": y}})
        self.nodes.append(node)
        return node

    def create_point_list(self, points: List[Tuple[float, float]], position: Tuple[float, float], randomize: bool = False, switch_distance: float = 1.0) -> Node:
        point_dicts = [{"x": x, "y": y} for x, y in points]
        node = Node(NodeType.POINT_LIST.value, position, out_pins=[self._create_pin("Pos", PinType.VECTOR2)], 
                   config={"pointList": point_dicts, "randomize": randomize, "switchDistance": switch_distance})
        self.nodes.append(node)
        return node

    def create_move_to(self, position: Tuple[float, float], teleport: bool = False, teleport_once: bool = False) -> Node:
        node = Node(NodeType.MOVE_TO.value, position, 
                   in_pins=[self._create_pin("In"), self._create_pin("Position", PinType.VECTOR2)],
                   out_pins=[self._create_pin("Out")],
                   config={"teleport": teleport, "teleportOnce": teleport_once})
        self.nodes.append(node)
        return node

    def create_enter_portal(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.ENTER_PORTAL.value, position, in_pins=[self._create_pin("In"), self._create_pin("Portal ID", PinType.FLOAT)], out_pins=[self._create_pin("Out")])
        self.nodes.append(node)
        return node

    def create_map_change(self, map_name: str, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.MAP_CHANGE.value, position, in_pins=[self._create_pin("In")], config={"mapName": map_name})
        self.nodes.append(node)
        return node

    def create_operator(self, position: Tuple[float, float], operator_type: int = 0, towards_distance: float = 0.0) -> Node:
        node = Node(NodeType.OPERATOR.value, position,
                   in_pins=[
                       self._create_pin("A", PinType.VECTOR2),
                       self._create_pin("B", PinType.VECTOR2),
                       self._create_pin("Val", PinType.FLOAT)
                   ],
                   out_pins=[
                       self._create_pin("Result", PinType.VECTOR2),
                       self._create_pin("Distance", PinType.FLOAT)
                   ],
                   config={"operatorType": operator_type, "towardsDistance": towards_distance})
        self.nodes.append(node)
        return node

    def create_comparison(self, position: Tuple[float, float], comparison_type: int = 0, val_to_compare: float = 0.0) -> Node:
        node = Node(NodeType.COMPARISON.value, position,
                   in_pins=[self._create_pin("A", PinType.FLOAT)],
                   out_pins=[self._create_pin("Result", PinType.BOOLEAN)],
                   config={"comparisonType": comparison_type, "valToCompare": val_to_compare})
        self.nodes.append(node)
        return node

    def create_save_pos(self, position: Tuple[float, float], persistent: bool = False) -> Node:
        node = Node(NodeType.SAVE_POS.value, position,
                   in_pins=[self._create_pin("In"), self._create_pin("Pos", PinType.VECTOR2)],
                   out_pins=[
                       self._create_pin("Out"),
                       self._create_pin("Saved Pos", PinType.VECTOR2),
                       self._create_pin("Has Value", PinType.BOOLEAN)
                   ],
                   config={"persistentPos": persistent})
        self.nodes.append(node)
        return node

    def create_use_item(self, item_id: int, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.USE_ITEM.value, position,
                   in_pins=[self._create_pin("In")],
                   out_pins=[self._create_pin("Out"), self._create_pin("Has", PinType.BOOLEAN)],
                   config={"itemId": item_id})
        self.nodes.append(node)
        return node

    def create_send_message(self, message: str, position: Tuple[float, float], delay_ms: int = 0) -> Node:
        node = Node(NodeType.SEND_MESSAGE.value, position,
                   in_pins=[self._create_pin("In")],
                   out_pins=[self._create_pin("Out")],
                   config={"message": message, "delayMs": delay_ms, "sendWithDelay": delay_ms > 0})
        self.nodes.append(node)
        return node

    def create_received_message(self, from_player: str, content: str, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.RECEIVE_MESSAGE.value, position,
                   in_pins=[self._create_pin("In")],
                   out_pins=[self._create_pin("Out")],
                   config={"from": from_player, "content": content})
        self.nodes.append(node)
        return node

    def create_group(self, position: Tuple[float, float], epsilon: float = 0.1, max_dist: float = 15.0) -> Node:
        node = Node(NodeType.GROUP.value, position,
                   out_pins=[self._create_pin("Center", PinType.VECTOR2)],
                   config={"epsilon": epsilon, "maxDistanceFromPlayer": max_dist})
        self.nodes.append(node)
        return node

    def create_hotkey(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.HOTKEY.value, position,
                   in_pins=[self._create_pin("None"), self._create_pin("Pressed"), self._create_pin("Held")],
                   out_pins=[self._create_pin("Out")],
                   config={"hotkeyName": "", "nodehotkey": {"isAlt": False, "isCtrl": False, "isShift": False, "key": 0}})
        self.nodes.append(node)
        return node

    def create_player_count(self, position: Tuple[float, float], exclude_wl: bool = True) -> Node:
        node = Node(NodeType.PLAYER_COUNT.value, position,
                   out_pins=[self._create_pin("Count", PinType.FLOAT)],
                   config={"excludeWLPlayers": exclude_wl})
        self.nodes.append(node)
        return node

    def create_status_level(self, position: Tuple[float, float], status_type: int = 0) -> Node:
        node = Node(NodeType.STATUS_LEVEL.value, position,
                   out_pins=[self._create_pin("Level", PinType.FLOAT)],
                   config={"statusType": status_type})
        self.nodes.append(node)
        return node

    def create_switch_server(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.SWITCH_SERVER.value, position,
                   out_pins=[self._create_pin("Out")])
        self.nodes.append(node)
        return node

    def create_connect_to_quest(self, position: Tuple[float, float], max_pop: int = 85) -> Node:
        node = Node(NodeType.CONNECT_TO_QUEST.value, position,
                   out_pins=[self._create_pin("Out")],
                   config={"selectedQuestType": [], "maxRealmPopCount": max_pop, "minRealmPopCount": 0})
        self.nodes.append(node)
        return node

    def create_nexus(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.NEXUS.value, position,
                   out_pins=[self._create_pin("Out")])
        self.nodes.append(node)
        return node

    def create_reset_tile_cache(self, position: Tuple[float, float]) -> Node:
        node = Node(NodeType.RESET_TILE_CACHE.value, position,
                   out_pins=[self._create_pin("Out")])
        self.nodes.append(node)
        return node

    def create_offset_pos(self, position: Tuple[float, float], dist: float = 1.0) -> Node:
        node = Node(NodeType.OFFSET_POS.value, position,
                   in_pins=[self._create_pin("Pos", PinType.VECTOR2)],
                   out_pins=[self._create_pin("Result", PinType.VECTOR2)],
                   config={"offsetDist": dist})
        self.nodes.append(node)
        return node

    # =========================================================================
    # COMPOSITE PATTERNS - Pre-built logic blocks
    # =========================================================================

    # Entity IDs for Nexus
    REALM_PORTAL_ID = 1810  # Realm Portal in Nexus (objectType=1)
    NEXUS_SPAWN_POINT = (127.0, 170.0)  # Default Nexus spawn/portal area

    def add_nexus_handler(self, base_x: float = 400, base_y: float = -1400) -> Dict[str, Node]:
        """
        Add standard Nexus handler logic block.

        Flow:
        MapChange("Nexus") -> Wait(500ms) -> MoveTo(spawn point)
            -> If(portal exists)
                -> True: MoveTo(portal) -> EnterPortal
                -> False: (loops/retries)

        Args:
            base_x: X position for rightmost node (MapChange)
            base_y: Y position baseline for the node row

        Returns:
            Dict of created nodes for optional further linking
        """
        # Node positions (right to left flow)
        map_change = self.create_map_change("Nexus", (base_x, base_y))
        wait = self.create_wait(500, (base_x - 200, base_y))

        # Spawn point data
        spawn_point = self.create_point(
            self.NEXUS_SPAWN_POINT[0],
            self.NEXUS_SPAWN_POINT[1],
            (base_x - 400, base_y + 150)
        )
        move_to_spawn = self.create_move_to((base_x - 400, base_y))

        # Portal detection
        portal_detector = self.create_enemy_list(
            [self.REALM_PORTAL_ID],
            (base_x - 800, base_y + 100),
            object_type=1  # Static object
        )

        # Conditional check
        if_portal = self.create_if_node((base_x - 600, base_y))

        # True branch: move to portal and enter
        move_to_portal = self.create_move_to((base_x - 800, base_y))
        enter_portal = self.create_enter_portal((base_x - 1000, base_y))

        # === EXECUTION LINKS ===
        # MapChange.In -> Wait.Out
        self.link_pins(map_change, "In", wait, "Out")
        # Wait.In -> MoveTo(spawn).Out
        self.link_pins(wait, "In", move_to_spawn, "Out")
        # MoveTo(spawn).In -> If.Out
        self.link_pins(move_to_spawn, "In", if_portal, "Out")
        # If.True -> MoveTo(portal).Out
        self.link_pins(if_portal, "True", move_to_portal, "Out")
        # MoveTo(portal).In -> EnterPortal.Out
        self.link_pins(move_to_portal, "In", enter_portal, "Out")

        # === DATA LINKS ===
        # Point.Pos -> MoveTo(spawn).Position
        self.link_pins(spawn_point, "Pos", move_to_spawn, "Position")
        # EnemyList.Exists -> If.Condition
        self.link_pins(portal_detector, "Exists", if_portal, "Condition")
        # EnemyList.Pos -> MoveTo(portal).Position
        self.link_pins(portal_detector, "Pos", move_to_portal, "Position")
        # EnemyList.ID -> EnterPortal.Portal ID
        self.link_pins(portal_detector, "ID", enter_portal, "Portal ID")

        return {
            "map_change": map_change,
            "wait": wait,
            "spawn_point": spawn_point,
            "move_to_spawn": move_to_spawn,
            "portal_detector": portal_detector,
            "if_portal": if_portal,
            "move_to_portal": move_to_portal,
            "enter_portal": enter_portal
        }

    def link_pins(self, source_node: Node, source_pin_name: str, target_node: Node, target_pin_name: str):
        """
        Link two pins.
        NOTE: Execution flow is Source(In) -> Sink(Out).
        Data flow is Source(Out) -> Sink(In).
        This method takes 'source_node' as the one providing the value/signal (Output) 
        and 'target_node' as the one receiving (Input).
        
        For Execution (Inverted):
        source_node should be the Trigger (Start, If.True). Pin name 'In', 'True'.
        target_node should be the Action (MoveTo). Pin name 'Out'.
        
        For Data (Standard):
        source_node should be Provider (EnemyList). Pin name 'Pos'.
        target_node should be Receiver (MoveTo). Pin name 'Position'.
        """
        # Find pins and track which array they come from
        source_pin = None
        source_is_out = False
        for pin in source_node.out_pins:
            if pin.name == source_pin_name:
                source_pin = pin
                source_is_out = True
                break
        if not source_pin:
            for pin in source_node.in_pins:
                if pin.name == source_pin_name:
                    source_pin = pin
                    source_is_out = False
                    break

        target_pin = None
        target_is_out = False
        for pin in target_node.in_pins:
            if pin.name == target_pin_name:
                target_pin = pin
                target_is_out = False
                break
        if not target_pin:
            for pin in target_node.out_pins:
                if pin.name == target_pin_name:
                    target_pin = pin
                    target_is_out = True
                    break

        if not source_pin or not target_pin:
            raise ValueError(f"Pin not found: {source_pin_name} -> {target_pin_name}")

        if source_pin.pin_type != target_pin.pin_type:
            raise ValueError(
                f"Type mismatch linking {source_pin.name}({source_pin.pin_type.value}) "
                f"to {target_pin.name}({target_pin.pin_type.value})"
            )

        # Actual convention (from working JSON files):
        # leftPinID = ALWAYS from outPins array
        # rightPinID = ALWAYS from inPins array
        if source_is_out and not target_is_out:
            # Data link: source(outPins) -> target(inPins)
            left_pin, right_pin = source_pin, target_pin
        elif not source_is_out and target_is_out:
            # Exec link: source(inPins) -> target(outPins), swap for JSON
            left_pin, right_pin = target_pin, source_pin
        else:
            raise ValueError(
                f"Invalid link: both pins from same array type. "
                f"source({source_pin_name}) is_out={source_is_out}, "
                f"target({target_pin_name}) is_out={target_is_out}"
            )

        # Prevent duplicate connections
        if any(l.left_pin_id == left_pin.id and l.right_pin_id == right_pin.id for l in self.links):
            raise ValueError(f"Duplicate link: {source_pin.name} -> {target_pin.name}")

        self.links.append(Link(left_pin.id, right_pin.id))

    def generate(self) -> str:
        result = {
            "links": [link.to_dict() for link in self.links],
            "nodes": [node.to_dict() for node in self.nodes],
            "version": "1.0"
        }
        return json.dumps(result, indent=4)

    def save(self, filename: str):
        with open(filename, 'w') as f:
            f.write(self.generate())
