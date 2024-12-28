from pathlib import Path
from typing import Dict, List, Optional

import yaml
from diagrams import Diagram, Cluster
from diagrams.aws.compute import ElasticContainerService as ECS
from diagrams.aws.network import (
    InternetGateway,
    Route53,
    RouteTable,
    VPC,
    PrivateSubnet,
    PublicSubnet,
    Nacl
)
from diagrams.aws.security import IAMRole
from diagrams.aws.general import General

from models import Edge, Node


# Mapping of AWS resource types to diagram nodes
RESOURCE_TO_NODE = {
    "aws_vpc": VPC,
    "aws_subnet": PublicSubnet,  # Default to PublicSubnet, could be made dynamic based on subnet type
    "aws_internet_gateway": InternetGateway,
    "aws_route_table": RouteTable,
    "aws_security_group": Nacl,  # Using Nacl as a stand-in for SecurityGroup
    "aws_iam_role": IAMRole,
    "aws_ecs_cluster": ECS,
    "aws_ecs_service": ECS,  # Use ECS for both cluster and service
    "aws_ecs_task_definition": ECS,
    "provider": General  # Use AWS General icon for provider blocks
}


def get_node_class(resource_type: str):
    """Get the appropriate diagram node class for a resource type."""
    # Handle provider blocks specially
    if resource_type.startswith("provider-"):
        return RESOURCE_TO_NODE["provider"]

    # Direct mapping
    if resource_type in RESOURCE_TO_NODE:
        return RESOURCE_TO_NODE[resource_type]
    
    # Try base type matching
    base_type = resource_type.split("_")[1]  # Remove 'aws_' prefix
    for key, value in RESOURCE_TO_NODE.items():
        if key.endswith(base_type):
            return value
    return None


class DiagramGenerator:
    """Generates AWS architecture diagrams from YAML descriptions."""

    def __init__(self, yaml_file: Path):
        """Initialize with YAML file containing diagram description."""
        if not yaml_file.exists():
            raise ValueError(f"YAML file not found: {yaml_file}")

        with yaml_file.open() as f:
            data = yaml.safe_load(f)
            if not data:
                raise ValueError("Empty YAML file")

            self.yaml_nodes = data.get("nodes", [])
            self.yaml_edges = data.get("edges", [])
            self._node_map: Dict[str, object] = {}
            self._cluster_map: Dict[str, Cluster] = {}

    def generate(self, output_file: str):
        """Generate diagram from YAML description."""
        with Diagram(
            "AWS Infrastructure",
            filename=output_file,
            show=False,
            direction="LR"
        ):
            self._create_nodes()
            self._create_edges()

    def _get_or_create_cluster(self, cluster_id: str, label: str) -> Cluster:
        """Get existing cluster or create a new one."""
        if cluster_id not in self._cluster_map:
            self._cluster_map[cluster_id] = Cluster(label)
        return self._cluster_map[cluster_id]

    def _get_cluster_nodes(self) -> Dict[str, set[str]]:
        """Get all nodes that should be in each cluster, including indirectly related nodes."""
        # Initialize with direct parent relationships
        cluster_nodes: Dict[str, set[str]] = {}
        for node in self.yaml_nodes:
            if parent := node.get("parent"):
                if parent not in cluster_nodes:
                    cluster_nodes[parent] = set()
                cluster_nodes[parent].add(node["id"])

        # Build adjacency list from edges
        adjacency: Dict[str, set[str]] = {}
        for edge in self.yaml_edges:
            source = edge["source"]
            target = edge["target"]
            if source not in adjacency:
                adjacency[source] = set()
            if target not in adjacency:
                adjacency[target] = set()
            adjacency[source].add(target)
            adjacency[target].add(source)  # Bidirectional for cluster membership

        # For each cluster, add nodes that are connected to its members
        changed = True
        while changed:
            changed = False
            for cluster_id, members in cluster_nodes.items():
                new_members = set()
                for member in members:
                    if member in adjacency:
                        for connected in adjacency[member]:
                            if connected not in members and not any(
                                connected in other_members 
                                for other_id, other_members in cluster_nodes.items() 
                                if other_id != cluster_id
                            ):
                                new_members.add(connected)
                if new_members:
                    changed = True
                    members.update(new_members)

        return cluster_nodes

    def _get_resource_name(self, node_id: str) -> str:
        """Extract the resource name from node ID or identifier."""
        # Try to get from identifier first
        node = next((n for n in self.yaml_nodes if n["id"] == node_id), None)
        if node and (identifier := node.get("identifier")):
            # Extract resource name from terraform identifier (e.g., "aws_vpc.main" -> "main")
            return identifier.split(".")[-1]
        
        # Fallback to node ID
        parts = node_id.split("-")
        return parts[-1] if len(parts) > 1 else node_id

    def _get_node_label(self, node_id: str) -> str:
        """Get a two-line label with resource identifier and name."""
        node = next((n for n in self.yaml_nodes if n["id"] == node_id), None)
        if not node:
            return node_id

        # Special handling for provider blocks
        if node_id.startswith("provider-"):
            # Extract provider name and region from identifier
            # e.g., "aws.provider.us-west-2" -> "aws\nus-west-2"
            if identifier := node.get("identifier"):
                parts = identifier.split(".")
                if len(parts) >= 3:
                    return f"{parts[0]}\n{parts[-1]}"
            return node_id

        # Get resource identifier (e.g., aws_vpc)
        resource_type = node_id.split("-")[0]
        
        # Get resource name from identifier or node ID
        if identifier := node.get("identifier"):
            # Extract name from terraform identifier (e.g., "aws_vpc.main" -> "main")
            name = identifier.split(".")[-1]
        else:
            # Fallback to last part of node ID
            parts = node_id.split("-")
            name = parts[-1] if len(parts) > 1 else node_id

        return f"{resource_type}\n{name}"

    def _create_nodes(self):
        """Create diagram nodes from YAML description."""
        # First pass: create clusters and determine cluster membership
        cluster_nodes = self._get_cluster_nodes()
        
        # Create clusters first
        for node in self.yaml_nodes:
            node_id = node["id"]
            if node_id in cluster_nodes:
                # Use two-line label for clusters
                label = self._get_node_label(node_id)
                self._get_or_create_cluster(node_id, label)

        # Second pass: create nodes in their clusters
        for node in self.yaml_nodes:
            node_id = node["id"]
            if node_id in self._node_map:
                continue

            # Skip if this is a cluster itself
            if node_id in cluster_nodes:
                continue

            # Use two-line label for nodes
            label = self._get_node_label(node_id)
            node_cluster = next(
                (cluster_id for cluster_id, members in cluster_nodes.items() 
                 if node_id in members),
                None
            )

            # Get node class based on resource type
            resource_type = node_id.split("-")[0]
            node_class = get_node_class(resource_type)
            
            if not node_class:
                continue

            # Create node in appropriate context
            if node_cluster:
                with self._get_or_create_cluster(node_cluster, ""):
                    self._node_map[node_id] = node_class(label)
            else:
                self._node_map[node_id] = node_class(label)

    def _create_edges(self):
        """Create edges between nodes from YAML description."""
        for edge in self.yaml_edges:
            source = self._node_map.get(edge["source"])
            target = self._node_map.get(edge["target"])
            if source and target:
                source >> target


def generate_diagram(diagram_file: Path, output_file: str = "infrastructure") -> None:
    """Generate an AWS infrastructure diagram from a YAML file."""
    generator = DiagramGenerator(diagram_file)
    generator.generate(output_file)
