#!/usr/bin/env python3

import argparse
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from mappings import create_diagram_nodes, create_diagram_edges, write_diagram_yaml
from models import FileInfo, ResourceBlock


class FileHandler(ABC):
    @abstractmethod
    def can_handle(self, file_path: Path) -> bool:
        pass

    @abstractmethod
    def process(self, file_path: Path) -> FileInfo:
        pass


class TerraformFileHandler(FileHandler):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix == '.tf'

    def process(self, file_path: Path) -> FileInfo:
        stats = file_path.stat()
        with file_path.open('r') as f:
            content = f.read()
        return FileInfo(
            path=file_path,
            size=stats.st_size,
            modified_time=stats.st_mtime,
            content=content
        )


class TerraformVarsFileHandler(FileHandler):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix == '.tfvars'

    def process(self, file_path: Path) -> FileInfo:
        stats = file_path.stat()
        with file_path.open('r') as f:
            content = f.read()
        return FileInfo(
            path=file_path,
            size=stats.st_size,
            modified_time=stats.st_mtime,
            content=content
        )


class FileScanner:
    def __init__(self, handlers: List[FileHandler]):
        self.handlers = handlers

    def scan_directory(self, directory: Path) -> List[FileInfo]:
        results = []

        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                for handler in self.handlers:
                    if handler.can_handle(file_path):
                        results.append(handler.process(file_path))
                        break

        return results


def extract_resource_blocks(content: str) -> List[ResourceBlock]:
    blocks = []
    current_block = []
    brace_count = 0
    in_block = False
    resource_type = None
    resource_name = None

    for line in content.splitlines():
        stripped = line.strip()

        if not in_block and stripped.startswith('resource'):
            parts = stripped.split('"')
            if len(parts) >= 4:
                resource_type = parts[1]
                resource_name = parts[3]
                in_block = True

        if in_block:
            current_block.append(line)
            brace_count += line.count('{')
            brace_count -= line.count('}')

            if brace_count == 0:
                in_block = False
                if resource_type and resource_name:
                    block_content = '\n'.join(current_block)
                    # Extract the actual name from the name field in the block
                    actual_name = None
                    for line in current_block:
                        if 'name' in line and '=' in line:
                            name_parts = line.split('=')
                            if len(name_parts) >= 2:
                                actual_name = name_parts[1].strip().strip('"')
                                break

                    blocks.append(ResourceBlock(
                        type=resource_type,
                        name=actual_name or resource_name,
                        content=block_content,
                        identifier=f"{resource_type}.{resource_name}"
                    ))
                current_block = []
                resource_type = None
                resource_name = None

    return blocks


def main():
    parser = argparse.ArgumentParser(
        description='Scan directory for Terraform files'
    )
    parser.add_argument(
        'directory',
        help='Directory to scan for Terraform files'
    )
    parser.add_argument(
        '--output',
        default='infrastructure',
        help='Output filename for the diagram (without extension)'
    )
    args = parser.parse_args()

    scan_path = Path(args.directory)
    if not scan_path.is_dir():
        print(f"Error: {args.directory} is not a directory")
        return 1

    handlers = [
        TerraformFileHandler(),
        TerraformVarsFileHandler()
    ]

    scanner = FileScanner(handlers)
    results = scanner.scan_directory(scan_path)

    # Collect all blocks from all files
    all_blocks = []

    for file_info in results:
        # Extract resource blocks from each file
        blocks = extract_resource_blocks(file_info.content)
        all_blocks.extend(blocks)

    # Print summary
    print(f"\nTotal resources found: {len(all_blocks)}")
    print("\nResource types:")
    resource_types = {}
    for block in all_blocks:
        resource_types[block.type] = resource_types.get(block.type, 0) + 1
    for resource_type, count in sorted(resource_types.items()):
        print(f"  {resource_type}: {count}")

    # Create diagram nodes and edges
    nodes = create_diagram_nodes(all_blocks)
    edges = create_diagram_edges(all_blocks)
    
    # Print edge summary
    print(f"\nTotal edges found: {len(edges)}")
    for edge in edges:
        print(f"  {edge.source} -> {edge.target}")

    # Save diagram YAML
    diagram_path = scan_path / "diagram.yaml"
    write_diagram_yaml(nodes, diagram_path, edges)
    print(f"\nDiagram YAML saved to {diagram_path}")

    # Generate visual diagram if diagrams module is available
    try:
        from diagram_generator import generate_diagram
        generate_diagram(diagram_path, args.output)
        print(f"\nVisual diagram saved to {args.output}.png")
    except ImportError:
        print("\nWarning: diagrams module not available. Install it with: pip install diagrams")
        print("Visual diagram generation skipped.")

    return 0


if __name__ == "__main__":
    exit(main())
