from typing import List
from core.entities import Paper
from datetime import datetime
import re

class RankingEngine:
    def __init__(self):
        # Weights for the composite score
        self.weights = {
            'similarity': 0.40,
            'citations': 0.25,
            'recency': 0.20,
            'abstract_length': 0.05,
            'title_keyword': 0.10
        }
        self.current_year = datetime.now().year

    def _normalize_citations(self, papers: List[Paper]) -> List[float]:
        citations = [p.citations if p.citations is not None else 0 for p in papers]
        if not citations:
            return []
        max_cit = max(citations)
        if max_cit == 0:
            return [0.0] * len(papers)
        return [c / max_cit for c in citations]

    def _calculate_recency_score(self, year: int) -> float:
        if not year:
            return 0.5 # Default to middle if unknown
        age = self.current_year - year
        if age < 0:
            return 1.0 # Future/current year
        # Decay function: 1.0 for new, approaches 0 for very old (e.g., > 20 years)
        return max(0.0, 1.0 - (age / 20.0))

    def _calculate_abstract_score(self, abstract: str) -> float:
        """Rewards abstracts that are detailed but not excessively long."""
        if not abstract:
            return 0.0
        length = len(abstract)
        # Optimal length between 500 and 2000 characters
        if 500 <= length <= 2000:
            return 1.0
        elif length < 500:
            return length / 500.0
        else:
            return max(0.5, 2000.0 / length)

    def _calculate_title_keyword_score(self, query: str, title: str) -> float:
        """Checks if exact query keywords appear in the title."""
        if not query or not title:
            return 0.0
        
        keywords = [k.strip().lower() for k in query.split(',')]
        title_lower = title.lower()
        
        matched = sum(1 for k in keywords if k in title_lower)
        return matched / len(keywords) if keywords else 0.0

    def rank_papers(self, query: str, papers: List[Paper]) -> List[Paper]:
        """Calculates final composite score and sorts papers."""
        if not papers:
            return []

        norm_citations = self._normalize_citations(papers)

        for idx, paper in enumerate(papers):
            sim_score = (paper.similarity_score or 0.0) * self.weights['similarity']
            cit_score = norm_citations[idx] * self.weights['citations']
            rec_score = self._calculate_recency_score(paper.year) * self.weights['recency']
            abs_score = self._calculate_abstract_score(paper.abstract) * self.weights['abstract_length']
            title_score = self._calculate_title_keyword_score(query, paper.title) * self.weights['title_keyword']

            paper.final_score = round(sim_score + cit_score + rec_score + abs_score + title_score, 4)

        # Sort descending by final score
        return sorted(papers, key=lambda p: p.final_score, reverse=True)
