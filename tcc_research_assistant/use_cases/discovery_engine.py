from typing import List
from datetime import datetime
from core.entities import Paper
from use_cases.search_interactor import SearchInteractor
import logging

class DiscoveryEngine:
    """Takes a highly ranked paper and performs an automated search to find related works
    based on keywords from its title and abstract."""
    
    def __init__(self, interactor: SearchInteractor):
        self.interactor = interactor

    def discover_related(self, source_paper: Paper, max_results: int = 5) -> List[Paper]:
        logging.info(f"Starting discovery for related papers for: {source_paper.title}")
        
        # Simplified discovery heuristic: use main words from title, minus stop words
        # In a real system, you'd extract entities from the abstract using TF-IDF or spaCy
        stop_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'on', 'at', 'to', 'from', 'by', 'of'}
        words = source_paper.title.replace(',', ' ').split()
        keywords = [w for w in words if w.lower() not in stop_words and len(w) > 3][:3]
        
        query_str = ",".join(keywords)
        
        if not query_str:
             return []

        # Execute a shallow related search (e.g., within the last 5 years)
        current_year = datetime.now().year
        related_papers = self.interactor.execute_search(
            query=query_str, 
            max_results=max_results, 
            year_start=current_year - 5
        )
        
        # Exclude the source paper itself
        related_papers = [p for p in related_papers if p.title.lower() != source_paper.title.lower()]
        
        source_paper.related_papers = [p.title for p in related_papers]
        return related_papers
