import os
import tempfile
from pathlib import Path
from unittest import TestCase

import yaml

from mappings import Node, create_diagram_nodes, write_diagram_yaml
from tf_scanner import ResourceBlock


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
