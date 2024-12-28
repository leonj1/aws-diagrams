#!/usr/bin/env python3

import argparse
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class ResourceBlock:
    type: str
    name: str
    content: str
    identifier: str


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


@dataclass
class FileInfo:
    path: Path
    size: int
    modified_time: float


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
        return FileInfo(
            path=file_path,
            size=stats.st_size,
            modified_time=stats.st_mtime
        )


class TerraformVarsFileHandler(FileHandler):
    def can_handle(self, file_path: Path) -> bool:
        return file_path.suffix == '.tfvars'

    def process(self, file_path: Path) -> FileInfo:
        stats = file_path.stat()
        return FileInfo(
            path=file_path,
            size=stats.st_size,
            modified_time=stats.st_mtime
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


def main():
    parser = argparse.ArgumentParser(
        description='Scan directory for Terraform files'
    )
    parser.add_argument(
        'directory',
        help='Directory to scan for Terraform files'
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

    for file_info in results:
        print(f"Found: {file_info.path}")
        print(f"  Size: {file_info.size} bytes")
        print(f"  Modified: {file_info.modified_time}")
        print()

    return 0


if __name__ == "__main__":
    exit(main())
