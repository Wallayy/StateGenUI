"""
Database module - Data files and scraping utilities.

Exposes the Unified Data Manager.
"""

from .entity_index import EntityIndex
from .dungeon_database import DungeonDatabase
from .loot_database import LootDatabase
from .manager import AppDatabase, get_db
