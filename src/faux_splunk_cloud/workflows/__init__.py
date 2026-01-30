"""
Workflow engine for threat intelligence processing.

This module implements a MineMeld-compatible workflow system with:
- Miners: Input nodes that fetch indicators from external sources
- Processors: Transform nodes that aggregate, filter, and enrich indicators
- Outputs: Export nodes that send indicators to consumers

The workflow engine supports WYSIWYG visual editing through the Backstage UI.
"""

from .prototypes import (
    WorkflowPrototype,
    PrototypeType,
    MINER_PROTOTYPES,
    PROCESSOR_PROTOTYPES,
    OUTPUT_PROTOTYPES,
    get_prototype,
    list_prototypes,
)
from .models import (
    Workflow,
    WorkflowNode,
    WorkflowEdge,
    WorkflowStatus,
    Indicator,
    IndicatorType,
    ShareLevel,
)
from .engine import WorkflowEngine, get_workflow_engine

__all__ = [
    # Prototypes
    "WorkflowPrototype",
    "PrototypeType",
    "MINER_PROTOTYPES",
    "PROCESSOR_PROTOTYPES",
    "OUTPUT_PROTOTYPES",
    "get_prototype",
    "list_prototypes",
    # Models
    "Workflow",
    "WorkflowNode",
    "WorkflowEdge",
    "WorkflowStatus",
    "Indicator",
    "IndicatorType",
    "ShareLevel",
    # Engine
    "WorkflowEngine",
    "get_workflow_engine",
]
