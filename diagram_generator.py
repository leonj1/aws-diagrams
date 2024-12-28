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
    "aws_ecs_task_definition": ECS
}


def get_node_class(resource_type: str):
    """Get the appropriate diagram node class for a resource type."""
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

    def _create_nodes(self):
        """Create diagram nodes from YAML description."""
        # First pass: create clusters
        for node in self.yaml_nodes:
            if node.get("parent"):
                parent_id = node["parent"]
                parent_label = next(
                    (n["label"] for n in self.yaml_nodes if n["id"] == parent_id),
                    parent_id.title()
                )
                self._get_or_create_cluster(parent_id, parent_label)

        # Second pass: create nodes
        for node in self.yaml_nodes:
            node_id = node["id"]
            if node_id in self._node_map:
                continue

            # Skip if this is a cluster
            if any(n.get("parent") == node_id for n in self.yaml_nodes):
                continue

            label = node.get("label", node_id)
            parent_id = node.get("parent")

            # Get node class based on resource type
            resource_type = node_id.split("-")[0]
            node_class = get_node_class(resource_type)
            
            if not node_class:
                continue

            # Create node in appropriate context
            if parent_id:
                with self._get_or_create_cluster(parent_id, ""):
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
