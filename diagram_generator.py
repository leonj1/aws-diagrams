from pathlib import Path
from typing import Dict, List, Optional

import yaml
from diagrams import Diagram
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
    def __init__(self, diagram_file: Path):
        """Initialize diagram generator with YAML file path."""
        self.diagram_file = diagram_file
        self.nodes: Dict[str, object] = {}
        self.edges: List[Edge] = []
        self._load_diagram()

    def _load_diagram(self) -> None:
        """Load diagram data from YAML file."""
        with self.diagram_file.open() as f:
            data = yaml.safe_load(f)
            
        if not data:
            raise ValueError("Empty diagram file")
            
        self.yaml_nodes = data.get("nodes", [])
        self.yaml_edges = data.get("edges", [])

    def _create_node(self, node_data: Dict) -> Optional[object]:
        """Create a diagram node from node data."""
        if not node_data.get("identifier"):
            return None
            
        resource_type = node_data["identifier"].split(".")[0]
        node_class = get_node_class(resource_type)
        
        if node_class:
            # Create the node and store it for edge creation
            node = node_class(node_data["label"])
            self.nodes[node_data["id"]] = node
            return node
            
        return None

    def generate(self, output_file: str = "infrastructure") -> None:
        """Generate the infrastructure diagram."""
        with Diagram(
            "AWS Infrastructure",
            filename=output_file,
            show=False,
            direction="TB"
        ):
            # First pass: create all nodes
            for node_data in self.yaml_nodes:
                self._create_node(node_data)
            
            # Second pass: create all edges
            for edge_data in self.yaml_edges:
                source_node = self.nodes.get(edge_data["source"])
                target_node = self.nodes.get(edge_data["target"])
                
                if source_node and target_node:
                    source_node >> target_node
                else:
                    print(f"Warning: Skipping edge from {edge_data['source']} to {edge_data['target']} due to missing node")


def generate_diagram(diagram_file: Path, output_file: str = "infrastructure") -> None:
    """Generate an AWS infrastructure diagram from a YAML file."""
    generator = DiagramGenerator(diagram_file)
    generator.generate(output_file)
