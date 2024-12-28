from pathlib import Path
from typing import Dict, List, Optional
import re
import yaml

from models import Node, ResourceBlock, Edge


# these are aws resources that can have child resources
can_be_parent = [
    "aws_vpc",
    "aws_subnet",
    "aws_ecs_cluster",
    "aws_ecs_service"
]


def get_resource_parent(resource_type: str) -> Optional[str]:
    parent_mappings = {
        "aws_vpc": "region",
        "aws_subnet": "vpc",
        "aws_lb": "vpc",
        "aws_ecs_service": "private-subnet",
        "aws_ecs_cluster": "private-subnet",
        "aws_cloudfront_distribution": None,
        "aws_waf_web_acl": None,
        "aws_wafregional_web_acl": "region"
    }
    return parent_mappings.get(resource_type)


def get_resource_label(resource_type: str, name: str) -> str:
    type_labels = {
        "aws_vpc": "VPC",
        "aws_subnet": "Subnet",
        "aws_lb": "Load Balancer",
        "aws_ecs_service": "ECS Service",
        "aws_ecs_cluster": "ECS Cluster",
        "aws_cloudfront_distribution": "CloudFront",
        "aws_waf_web_acl": "WAF",
        "aws_wafregional_web_acl": "Regional WAF"
    }
    base_label = type_labels.get(resource_type, resource_type.replace("aws_", "").replace("_", " ").title())
    return f"{base_label}: {name}"


def extract_resource_references(content: str) -> List[str]:
    """Extract Terraform resource references from a string."""
    # Match patterns like aws_iam_role.ecs_task_execution_role.name
    # but exclude the property at the end (like .name, .id, .arn)
    pattern = r'(?:^|\s|=|\(|\[)([a-zA-Z0-9_]+\.[a-zA-Z0-9_]+)(?:\.[a-zA-Z0-9_]+)?(?=\s|$|\)|\]|,)'
    matches = re.finditer(pattern, content)
    return [match.group(1) for match in matches]


def create_edges_from_block(block: ResourceBlock) -> List[Edge]:
    """Create edges from a resource block by finding references to other resources."""
    edges = []
    # Skip the resource declaration line
    content_lines = block.content.splitlines()[1:-1]
    content = '\n'.join(content_lines)
    
    # Find all resource references in the content
    references = extract_resource_references(content)
    
    # Create edges for each reference
    for target in references:
        # Skip self-references
        if target != block.identifier:
            edges.append(Edge(
                source=block.identifier,
                target=target
            ))
    
    return edges


def create_diagram_edges(resources: List[ResourceBlock]) -> List[Edge]:
    """Create edges between resources based on their references."""
    all_edges = []
    for resource in resources:
        edges = create_edges_from_block(resource)
        all_edges.extend(edges)
    return all_edges


def create_diagram_nodes(resources: List[ResourceBlock]) -> List[Node]:
    # Start with default nodes
    nodes = [
        Node(id="aws-cloud", label="AWS Cloud"),
        Node(id="region", label="AWS Region", parent="aws-cloud")
    ]

    # Add nodes for each resource
    for resource in resources:
        node_id = resource.identifier.replace(".", "-")
        parent = get_resource_parent(resource.type)
        label = get_resource_label(resource.type, resource.name)
        identifier = resource.identifier

        nodes.append(Node(
            id=node_id,
            label=label,
            parent=parent,
            identifier=identifier
        ))

    return nodes


def write_diagram_yaml(nodes: List[Node], output_file: Path, edges: Optional[List[Edge]] = None) -> None:
    node_dicts = []
    for node in nodes:
        node_dict = {
            "id": node.id,
            "identifier": node.identifier,
            "label": node.label
        }
        if node.parent:
            node_dict["parent"] = node.parent
        node_dicts.append(node_dict)

    yaml_content = {"nodes": node_dicts}
    
    if edges:
        edge_dicts = []
        for edge in edges:
            edge_dict = {
                "source": edge.source.replace(".", "-"),
                "target": edge.target.replace(".", "-")
            }
            if edge.label:
                edge_dict["label"] = edge.label
            edge_dicts.append(edge_dict)
        yaml_content["edges"] = edge_dicts

    with output_file.open("w") as f:
        yaml.safe_dump(yaml_content, f, sort_keys=False, indent=2)
