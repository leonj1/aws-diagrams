import tempfile
from pathlib import Path
from unittest import TestCase

import yaml

from diagrams import Diagram
from diagrams.aws.compute import ElasticContainerService as ECS
from diagrams.aws.network import VPC, PublicSubnet, Nacl

from diagram_generator import DiagramGenerator, get_node_class


class TestDiagramGenerator(TestCase):
    def setUp(self):
        self.test_diagram = {
            "nodes": [
                {
                    "id": "aws-cloud",
                    "identifier": None,
                    "label": "AWS Cloud"
                },
                {
                    "id": "aws_vpc-main",
                    "identifier": "aws_vpc.main",
                    "label": "VPC: main",
                    "parent": "region"
                },
                {
                    "id": "aws_ecs_cluster-main",
                    "identifier": "aws_ecs_cluster.main",
                    "label": "ECS Cluster: main",
                    "parent": "public-subnet"
                }
            ],
            "edges": [
                {
                    "source": "aws_ecs_cluster-main",
                    "target": "aws_vpc-main"
                }
            ]
        }

    def test_get_node_class(self):
        """Test node class mapping."""
        self.assertEqual(get_node_class("aws_vpc"), VPC)
        self.assertEqual(get_node_class("aws_ecs_cluster"), ECS)
        self.assertEqual(get_node_class("aws_ecs_service"), ECS)  # Should use ECS for service
        self.assertEqual(get_node_class("aws_subnet"), PublicSubnet)  # Should use PublicSubnet for subnet
        self.assertEqual(get_node_class("aws_security_group"), Nacl)  # Should use Nacl for security group
        self.assertIsNone(get_node_class("aws_unknown_resource"))

    def test_diagram_generator_initialization(self):
        """Test DiagramGenerator initialization with YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix=".yaml", delete=False) as tmp:
            yaml.safe_dump(self.test_diagram, tmp)
            tmp_path = Path(tmp.name)

        try:
            generator = DiagramGenerator(tmp_path)
            self.assertEqual(len(generator.yaml_nodes), 3)
            self.assertEqual(len(generator.yaml_edges), 1)
        finally:
            tmp_path.unlink()

    def test_diagram_generator_empty_file(self):
        """Test DiagramGenerator with empty YAML file."""
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as tmp:
            tmp_path = Path(tmp.name)

        try:
            with self.assertRaises(ValueError):
                DiagramGenerator(tmp_path)
        finally:
            tmp_path.unlink()
