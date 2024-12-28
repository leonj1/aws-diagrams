from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Edge:
    source: str
    target: str
    label: Optional[str] = None


@dataclass
class ResourceBlock:
    type: str
    name: str
    content: str
    identifier: str


@dataclass
class Node:
    id: str
    label: str
    parent: Optional[str] = None
    identifier: Optional[str] = None


@dataclass
class FileInfo:
    path: Path
    size: int
    modified_time: float
    content: str
