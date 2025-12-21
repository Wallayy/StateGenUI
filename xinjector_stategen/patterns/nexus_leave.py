from typing import Dict, Tuple
from xinjector_stategen.dag.state_generator import StateGenerator, Node

class NexusLeavePattern:
    """
    Pattern to handle leaving Nexus and entering Realm.
    """
    def __init__(self, generator: StateGenerator, spawn_point: Tuple[float, float], portal_id: int, wait_time: int):
        self.gen = generator
        self.spawn_point = spawn_point
        self.portal_id = portal_id
        self.wait_time = wait_time
        self.nodes = {}

    def build(self, x: float, y: float):
        # Create nodes
        self.nodes["map_change"] = self.gen.create_map_change("Nexus", (x, y))
        self.nodes["wait"] = self.gen.create_wait(self.wait_time, (x - 200, y))
        self.nodes["spawn_point"] = self.gen.create_point(self.spawn_point[0], self.spawn_point[1], (x - 400, y + 150))
        self.nodes["move_to_spawn"] = self.gen.create_move_to((x - 400, y))
        self.nodes["portal_detector"] = self.gen.create_enemy_list([self.portal_id], (x - 800, y + 100), object_type=1)
        self.nodes["if_portal"] = self.gen.create_if_node((x - 600, y))
        self.nodes["move_to_portal"] = self.gen.create_move_to((x - 800, y))
        self.nodes["enter_portal"] = self.gen.create_enter_portal((x - 1000, y))

        # Links
        self._link_exec("map_change", "In", "wait", "Out")
        self._link_exec("wait", "In", "move_to_spawn", "Out")
        self._link_exec("move_to_spawn", "In", "if_portal", "Out")
        self._link_exec("if_portal", "True", "move_to_portal", "Out")
        self._link_exec("move_to_portal", "In", "enter_portal", "Out")

        self.gen.link_pins(self.nodes["spawn_point"], "Pos", self.nodes["move_to_spawn"], "Position")
        self.gen.link_pins(self.nodes["portal_detector"], "Exists", self.nodes["if_portal"], "Condition")
        self.gen.link_pins(self.nodes["portal_detector"], "Pos", self.nodes["move_to_portal"], "Position")
        self.gen.link_pins(self.nodes["portal_detector"], "ID", self.nodes["enter_portal"], "Portal ID")

    def _link_exec(self, src_name, src_pin, tgt_name, tgt_pin):
        self.gen.link_pins(self.nodes[src_name], src_pin, self.nodes[tgt_name], tgt_pin)

    def get_nodes_dict(self) -> Dict[str, Node]:
        return self.nodes
