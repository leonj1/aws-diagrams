import os
import tempfile
from pathlib import Path
from unittest import TestCase

from tf_scanner import (
    FileInfo,
    FileScanner,
    TerraformFileHandler,
    TerraformVarsFileHandler
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
