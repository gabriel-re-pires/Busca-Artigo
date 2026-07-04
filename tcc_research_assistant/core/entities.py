from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Paper:
    title: str
    authors: List[str]
    year: Optional[int]
    abstract: str
    url: str
    source: str  # e.g., 'arXiv', 'Scholar'
    citations: int = 0
    language: str = "unknown"
    classification: str = "unknown"
    similarity_score: float = 0.0
    final_score: float = 0.0
    doi: Optional[str] = None
    related_papers: List[str] = field(default_factory=list)
