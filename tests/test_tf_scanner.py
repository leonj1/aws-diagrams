import os
import tempfile
from pathlib import Path
from unittest import TestCase

from tf_scanner import (
    FileInfo,
    FileScanner,
    ResourceBlock,
    TerraformFileHandler,
    TerraformVarsFileHandler,
    extract_resource_blocks
)


class TestTerraformScanner(TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_cases = [
            {
                "name": "terraform file",
                "file": "main.tf",
                "should_handle": True,
                "handler": TerraformFileHandler()
            },
            {
                "name": "terraform vars file",
                "file": "vars.tfvars",
                "should_handle": True,
                "handler": TerraformVarsFileHandler()
            },
            {
                "name": "non-terraform file",
                "file": "readme.md",
                "should_handle": False,
                "handler": TerraformFileHandler()
            }
        ]

    def test_file_handlers(self):
        for test in self.test_cases:
            with self.subTest(name=test["name"]):
                test_file = Path(self.temp_dir) / test["file"]
                test_file.touch()
                self.assertEqual(
                    test["handler"].can_handle(test_file),
                    test["should_handle"]
                )

    def test_file_scanner(self):
        handlers = [TerraformFileHandler(), TerraformVarsFileHandler()]
        scanner = FileScanner(handlers)

        test_file = Path(self.temp_dir) / "main.tf"
        test_file.touch()

        results = scanner.scan_directory(Path(self.temp_dir))
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], FileInfo)
        self.assertEqual(results[0].path, test_file)

    def tearDown(self):
        for root, _, files in os.walk(self.temp_dir):
            for file in files:
                os.remove(os.path.join(root, file))
        os.rmdir(self.temp_dir)


class TestResourceBlockExtraction(TestCase):
    def test_extract_single_resource(self):
        content = '''resource "aws_ecs_cluster" "main" {
  name = "react-cluster"
}'''
        blocks = extract_resource_blocks(content)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].type, "aws_ecs_cluster")
        self.assertEqual(blocks[0].name, "react-cluster")
        self.assertEqual(blocks[0].identifier, "aws_ecs_cluster.main")
        self.assertEqual(blocks[0].content, content)

    def test_extract_multiple_resources(self):
        content = '''resource "aws_ecs_cluster" "main" {
  name = "react-cluster"
}

resource "aws_iam_role" "ecs_task_execution_role" {
  name = "ecs-task-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}'''
        blocks = extract_resource_blocks(content)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].type, "aws_ecs_cluster")
        self.assertEqual(blocks[0].name, "react-cluster")
        self.assertEqual(blocks[0].identifier, "aws_ecs_cluster.main")
        self.assertEqual(blocks[1].type, "aws_iam_role")
        self.assertEqual(blocks[1].name, "ecs-task-execution-role")
        self.assertEqual(blocks[1].identifier, "aws_iam_role.ecs_task_execution_role")
