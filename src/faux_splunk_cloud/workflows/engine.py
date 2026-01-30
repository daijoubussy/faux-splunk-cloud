"""
Workflow execution engine.

Handles the execution of threat intelligence workflows,
processing indicators through miners, processors, and outputs.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable

from .models import (
    Workflow,
    WorkflowNode,
    WorkflowStatus,
    Indicator,
)
from .prototypes import get_prototype, PrototypeType

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """
    Engine for executing threat intelligence workflows.

    Manages workflow lifecycle, schedules executions, and
    routes indicators through the processing pipeline.
    """

    def __init__(self) -> None:
        """Initialize the workflow engine."""
        self._workflows: dict[str, Workflow] = {}
        self._running: dict[str, asyncio.Task] = {}
        self._node_handlers: dict[str, Callable] = {}

        # Register default handlers
        self._register_default_handlers()

    def _register_default_handlers(self) -> None:
        """Register default node type handlers."""
        # These are placeholder implementations
        # In production, each prototype would have a full implementation

        # Miner handlers
        self._node_handlers["taxii.client"] = self._handle_taxii_client
        self._node_handlers["rest.client"] = self._handle_rest_client
        self._node_handlers["csv.file"] = self._handle_csv_file
        self._node_handlers["localdb"] = self._handle_localdb

        # Processor handlers
        self._node_handlers["aggregator.generic"] = self._handle_aggregator
        self._node_handlers["aggregator.ipv4"] = self._handle_ipv4_aggregator
        self._node_handlers["filter.confidence"] = self._handle_confidence_filter
        self._node_handlers["filter.age"] = self._handle_age_filter
        self._node_handlers["filter.type"] = self._handle_type_filter
        self._node_handlers["enricher.whois"] = self._handle_whois_enricher
        self._node_handlers["enricher.geoip"] = self._handle_geoip_enricher
        self._node_handlers["tagger"] = self._handle_tagger

        # Output handlers
        self._node_handlers["edl.paloalto"] = self._handle_edl_output
        self._node_handlers["taxii.server"] = self._handle_taxii_server
        self._node_handlers["splunk.hec"] = self._handle_splunk_hec
        self._node_handlers["stix.bundle"] = self._handle_stix_bundle
        self._node_handlers["csv.export"] = self._handle_csv_export
        self._node_handlers["webhook"] = self._handle_webhook

    # =========================================================================
    # Workflow Management
    # =========================================================================

    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow with the engine."""
        self._workflows[workflow.id] = workflow
        logger.info(f"Registered workflow: {workflow.id} ({workflow.name})")

    def unregister_workflow(self, workflow_id: str) -> None:
        """Unregister a workflow from the engine."""
        if workflow_id in self._running:
            self._running[workflow_id].cancel()
            del self._running[workflow_id]

        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            logger.info(f"Unregistered workflow: {workflow_id}")

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        """List all registered workflows."""
        return list(self._workflows.values())

    # =========================================================================
    # Workflow Execution
    # =========================================================================

    async def execute_workflow(self, workflow_id: str) -> dict[str, Any]:
        """
        Execute a workflow.

        Args:
            workflow_id: ID of the workflow to execute

        Returns:
            Execution results including indicators processed
        """
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if workflow.status == WorkflowStatus.ACTIVE:
            raise ValueError(f"Workflow already running: {workflow_id}")

        logger.info(f"Starting workflow execution: {workflow_id}")
        workflow.status = WorkflowStatus.ACTIVE
        workflow.run_count += 1

        try:
            # Get execution order
            nodes = workflow.get_execution_order()
            logger.info(f"Execution order: {[n.id for n in nodes]}")

            # Track indicators flowing through the workflow
            node_outputs: dict[str, list[Indicator]] = {}
            total_processed = 0

            for node in nodes:
                if not node.enabled:
                    logger.debug(f"Skipping disabled node: {node.id}")
                    continue

                # Gather inputs from upstream nodes
                inputs: list[Indicator] = []
                for upstream in workflow.get_upstream_nodes(node.id):
                    if upstream.id in node_outputs:
                        inputs.extend(node_outputs[upstream.id])

                # Execute the node
                try:
                    outputs = await self._execute_node(node, inputs)
                    node_outputs[node.id] = outputs
                    node.indicators_processed += len(outputs)
                    total_processed += len(outputs)
                    node.last_run = datetime.utcnow()
                    node.last_error = None
                    logger.debug(f"Node {node.id} processed {len(inputs)} -> {len(outputs)} indicators")
                except Exception as e:
                    node.last_error = str(e)
                    logger.error(f"Node {node.id} failed: {e}")
                    raise

            workflow.last_run = datetime.utcnow()
            workflow.last_error = None
            workflow.status = WorkflowStatus.ACTIVE

            return {
                "workflow_id": workflow_id,
                "status": "completed",
                "indicators_processed": total_processed,
                "nodes_executed": len(nodes),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            workflow.status = WorkflowStatus.ERROR
            workflow.last_error = str(e)
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise

    async def pause_workflow(self, workflow_id: str) -> None:
        """Pause a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {workflow_id}")

        if workflow_id in self._running:
            self._running[workflow_id].cancel()
            del self._running[workflow_id]

        workflow.status = WorkflowStatus.PAUSED
        logger.info(f"Paused workflow: {workflow_id}")

    async def _execute_node(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """
        Execute a single node in the workflow.

        Args:
            node: The node to execute
            inputs: Input indicators (empty for miners)

        Returns:
            Output indicators
        """
        prototype = get_prototype(node.prototype)
        if not prototype:
            raise ValueError(f"Unknown prototype: {node.prototype}")

        handler = self._node_handlers.get(node.prototype)
        if not handler:
            logger.warning(f"No handler for prototype: {node.prototype}, passing through")
            return inputs

        return await handler(node, inputs)

    # =========================================================================
    # Node Handlers - Miners
    # =========================================================================

    async def _handle_taxii_client(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle TAXII client miner node."""
        # Placeholder implementation
        logger.info(f"TAXII client node {node.id}: would fetch from {node.config.get('url')}")
        return []

    async def _handle_rest_client(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle REST API client miner node."""
        logger.info(f"REST client node {node.id}: would fetch from {node.config.get('url')}")
        return []

    async def _handle_csv_file(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle CSV file miner node."""
        logger.info(f"CSV file node {node.id}: would read from {node.config.get('source')}")
        return []

    async def _handle_localdb(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle local database miner node."""
        indicators_data = node.config.get("indicators", [])
        indicators = []
        for data in indicators_data:
            if isinstance(data, dict):
                indicators.append(Indicator(**data))
            elif isinstance(data, str):
                # Assume IPv4 for simple string entries
                indicators.append(Indicator(type="ipv4", value=data))
        return indicators

    # =========================================================================
    # Node Handlers - Processors
    # =========================================================================

    async def _handle_aggregator(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle generic aggregator processor node."""
        dedup_key = node.config.get("dedup_key", "value")
        seen: dict[str, Indicator] = {}

        for indicator in inputs:
            key = getattr(indicator, dedup_key, indicator.value)
            if key not in seen:
                seen[key] = indicator
            else:
                # Merge confidence using configured method
                method = node.config.get("confidence_method", "max")
                existing = seen[key]
                if method == "max":
                    existing.confidence = max(existing.confidence, indicator.confidence)
                elif method == "min":
                    existing.confidence = min(existing.confidence, indicator.confidence)
                elif method == "avg":
                    existing.confidence = (existing.confidence + indicator.confidence) // 2

                # Merge sources if configured
                if node.config.get("merge_sources", True):
                    existing.sources.extend(indicator.sources)

        return list(seen.values())

    async def _handle_ipv4_aggregator(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle IPv4 aggregator processor node."""
        # Filter to IPv4 only
        ipv4_indicators = [i for i in inputs if i.type == "ipv4"]

        # Apply whitelist filtering
        whitelist = node.config.get("whitelist", [])
        if whitelist:
            # Placeholder: would implement CIDR matching
            pass

        # Deduplicate
        seen = {i.value: i for i in ipv4_indicators}
        return list(seen.values())

    async def _handle_confidence_filter(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle confidence filter processor node."""
        min_conf = node.config.get("min_confidence", 0)
        max_conf = node.config.get("max_confidence", 100)

        return [i for i in inputs if min_conf <= i.confidence <= max_conf]

    async def _handle_age_filter(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle age filter processor node."""
        from datetime import timedelta

        max_age_days = node.config.get("max_age_days", 30)
        use_first_seen = node.config.get("use_first_seen", False)
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)

        def is_recent(indicator: Indicator) -> bool:
            timestamp = indicator.first_seen if use_first_seen else indicator.last_seen
            return timestamp >= cutoff

        return [i for i in inputs if is_recent(i)]

    async def _handle_type_filter(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle type filter processor node."""
        include_types = set(node.config.get("include_types", []))
        exclude_types = set(node.config.get("exclude_types", []))

        def matches_filter(indicator: Indicator) -> bool:
            if include_types and indicator.type not in include_types:
                return False
            if indicator.type in exclude_types:
                return False
            return True

        return [i for i in inputs if matches_filter(i)]

    async def _handle_whois_enricher(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle WHOIS enricher processor node."""
        # Placeholder: would perform actual WHOIS lookups
        logger.info(f"WHOIS enricher node {node.id}: would enrich {len(inputs)} indicators")
        return inputs

    async def _handle_geoip_enricher(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle GeoIP enricher processor node."""
        # Placeholder: would perform GeoIP lookups
        logger.info(f"GeoIP enricher node {node.id}: would enrich {len(inputs)} indicators")
        return inputs

    async def _handle_tagger(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle tagger processor node."""
        add_tags = node.config.get("add_tags", [])
        remove_tags = set(node.config.get("remove_tags", []))
        replace_all = node.config.get("replace_all", False)

        for indicator in inputs:
            if replace_all:
                indicator.tags = list(add_tags)
            else:
                indicator.tags = [t for t in indicator.tags if t not in remove_tags]
                indicator.tags.extend(add_tags)

        return inputs

    # =========================================================================
    # Node Handlers - Outputs
    # =========================================================================

    async def _handle_edl_output(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle Palo Alto EDL output node."""
        include_type = node.config.get("include_type")
        max_entries = node.config.get("max_entries", 10000)

        filtered = [i for i in inputs if i.type == include_type][:max_entries]
        logger.info(f"EDL output node {node.id}: would export {len(filtered)} indicators")

        # Output nodes don't pass indicators downstream
        return []

    async def _handle_taxii_server(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle TAXII server output node."""
        logger.info(
            f"TAXII server node {node.id}: would serve {len(inputs)} indicators "
            f"in collection '{node.config.get('collection_title')}'"
        )
        return []

    async def _handle_splunk_hec(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle Splunk HEC output node."""
        url = node.config.get("url")
        index = node.config.get("index", "threat_intel")
        batch_size = node.config.get("batch_size", 100)

        logger.info(
            f"Splunk HEC node {node.id}: would send {len(inputs)} indicators "
            f"to {url} (index={index}, batch_size={batch_size})"
        )
        return []

    async def _handle_stix_bundle(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle STIX bundle output node."""
        output_path = node.config.get("output_path")
        logger.info(f"STIX bundle node {node.id}: would export {len(inputs)} indicators to {output_path}")
        return []

    async def _handle_csv_export(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle CSV export output node."""
        output_path = node.config.get("output_path")
        fields = node.config.get("fields", ["type", "value", "confidence"])
        logger.info(
            f"CSV export node {node.id}: would export {len(inputs)} indicators "
            f"to {output_path} (fields={fields})"
        )
        return []

    async def _handle_webhook(
        self,
        node: WorkflowNode,
        inputs: list[Indicator],
    ) -> list[Indicator]:
        """Handle webhook output node."""
        url = node.config.get("url")
        method = node.config.get("method", "POST")
        batch_size = node.config.get("batch_size", 100)

        logger.info(
            f"Webhook node {node.id}: would {method} {len(inputs)} indicators "
            f"to {url} (batch_size={batch_size})"
        )
        return []


# Global engine instance
_engine: WorkflowEngine | None = None


def get_workflow_engine() -> WorkflowEngine:
    """Get the global workflow engine instance."""
    global _engine
    if _engine is None:
        _engine = WorkflowEngine()
    return _engine
