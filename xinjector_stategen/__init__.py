"""
XInjector State Generator Package

Canonical library for generating XInjector state machine JSON files.
"""

from xinjector_stategen.dag.state_generator import StateGenerator
from xinjector_stategen.workflow_builder import WorkflowBuilder

__version__ = "1.0.0"
__all__ = ["StateGenerator", "WorkflowBuilder"]
