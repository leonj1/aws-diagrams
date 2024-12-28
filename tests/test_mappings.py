import os
import tempfile
from pathlib import Path
from unittest import TestCase

import yaml

from mappings import (
    create_diagram_nodes,
    create_edges_from_block,
    extract_resource_references,
    write_diagram_yaml
)
from models import Node, ResourceBlock, Edge


class TestMappings(TestCase):
    def test_create_diagram_nodes(self):
        resources = [
            ResourceBlock(
                type="aws_vpc",
                name="main",
                content='resource "aws_vpc" "main" {\n  name = "main"\n}',
                identifier="aws_vpc.main"
            ),
            ResourceBlock(
                type="aws_subnet",
                name="private",
                content='resource "aws_subnet" "private" {\n  name = "private"\n}',
                identifier="aws_subnet.private"
            )
        ]
        
        nodes = create_diagram_nodes(resources)
        
        # Check default nodes are present
        self.assertTrue(any(n.id == "aws-cloud" for n in nodes))
        self.assertTrue(any(n.id == "region" for n in nodes))
        
        # Check VPC node
        vpc_node = next(n for n in nodes if n.id == "aws_vpc-main")
        self.assertEqual(vpc_node.parent, "region")
        self.assertEqual(vpc_node.label, "VPC: main")
        
        # Check subnet node
        subnet_node = next(n for n in nodes if n.id == "aws_subnet-private")
        self.assertEqual(subnet_node.parent, "vpc")
        self.assertEqual(subnet_node.label, "Subnet: private")

    def test_write_diagram_yaml(self):
        nodes = [
            Node(id="aws-cloud", label="AWS Cloud"),
            Node(id="region", label="AWS Region", parent="aws-cloud"),
            Node(id="vpc", label="VPC", parent="region")
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            write_diagram_yaml(nodes, output_path)
            
            with output_path.open() as f:
                content = yaml.safe_load(f)
            
            self.assertIn("nodes", content)
            self.assertEqual(len(content["nodes"]), 3)
            
            # Check first node
            self.assertEqual(content["nodes"][0]["id"], "aws-cloud")
            self.assertEqual(content["nodes"][0]["label"], "AWS Cloud")
            self.assertNotIn("parent", content["nodes"][0])
            
            # Check node with parent
            self.assertEqual(content["nodes"][1]["id"], "region")
            self.assertEqual(content["nodes"][1]["parent"], "aws-cloud")
        
        finally:
            if output_path.exists():
                output_path.unlink()

    def test_extract_resource_references(self):
        content = '''
        role       = aws_iam_role.ecs_task_execution_role.name
        policy_arn = aws_ecs_cluster.cluster.id
        subnet_ids = [aws_subnet.private.id]
        vpc_id = aws_vpc.main.id
        '''
        
        references = extract_resource_references(content)
        expected = [
            "aws_iam_role.ecs_task_execution_role",
            "aws_ecs_cluster.cluster",
            "aws_subnet.private",
            "aws_vpc.main"
        ]
        self.assertEqual(sorted(references), sorted(expected))

    def test_create_edges_from_block(self):
        block = ResourceBlock(
            type="aws_iam_role_policy_attachment",
            name="ecs_task_execution_role_policy",
            identifier="aws_iam_role_policy_attachment.ecs_task_execution_role_policy",
            content='''resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = aws_ecs_cluster.cluster.id
}'''
        )
        
        edges = create_edges_from_block(block)
        self.assertEqual(len(edges), 2)
        
        # Check first edge
        self.assertEqual(edges[0].source, block.identifier)
        self.assertEqual(edges[0].target, "aws_iam_role.ecs_task_execution_role")
        
        # Check second edge
        self.assertEqual(edges[1].source, block.identifier)
        self.assertEqual(edges[1].target, "aws_ecs_cluster.cluster")

    def test_write_diagram_yaml_with_edges(self):
        nodes = [
            Node(id="node1", label="Node 1", identifier="aws_vpc.main"),
            Node(id="node2", label="Node 2", identifier="aws_subnet.private")
        ]
        
        edges = [
            Edge(source="aws_subnet.private", target="aws_vpc.main")
        ]
        
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            output_path = Path(tmp.name)
        
        try:
            write_diagram_yaml(nodes, output_path, edges)
            
            with output_path.open() as f:
                content = yaml.safe_load(f)
            
            self.assertIn("edges", content)
            self.assertEqual(len(content["edges"]), 1)
            
            # Check edge
            edge = content["edges"][0]
            self.assertEqual(edge["source"], "aws_subnet-private")
            self.assertEqual(edge["target"], "aws_vpc-main")
        
        finally:
            if output_path.exists():
                output_path.unlink()
