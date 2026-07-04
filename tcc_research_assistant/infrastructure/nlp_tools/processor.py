from ast import literal_eval
import re
from typing import List, Tuple
from core.entities import Paper
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import logging

try:
    from langdetect import detect
except ImportError:
    logging.warning("langdetect not installed. Language detection will fall back to 'unknown'")
    def detect(text): return "unknown"

class NLPProcessor:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words='english')
        
    def detect_language(self, text: str) -> str:
        if not text:
            return "unknown"
        try:
            return detect(text)
        except Exception as e:
            logging.error(f"Language detection failed: {e}")
            return "unknown"

    def classify_paper(self, paper: Paper) -> str:
        """Simple heuristic-based classification."""
        title_lower = paper.title.lower()
        abstract_lower = paper.abstract.lower() if paper.abstract else ""
        
        if "review" in title_lower or "survey" in title_lower:
            return "Review/Survey"
        elif "conference" in title_lower or "proceedings" in title_lower:
            return "Conference Paper"
        elif "thesis" in title_lower or "dissertation" in title_lower:
            return "Thesis"
        else:
            return "Journal Article (Presumed)"

    def calculate_similarity(self, query: str, papers: List[Paper]) -> List[Paper]:
        """Calculates TF-IDF and Cosine Similarity for a list of papers against the query."""
        if not papers:
            return papers

        # Combine title and abstract for a richer document representation
        documents = [f"{p.title} {p.abstract if p.abstract else ''}" for p in papers]
        
        # Include the query as the first document
        all_texts = [query] + documents
        
        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            # Calculate cosine similarity between query (index 0) and all papers
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            for idx, paper in enumerate(papers):
                paper.similarity_score = round(float(similarities[idx]), 4)
                
        except ValueError as e:
            logging.error(f"TF-IDF calculation failed (likely empty vocabulary): {e}")
            for paper in papers:
                 paper.similarity_score = 0.0

        return papers

    def process_papers(self, query: str, papers: List[Paper]) -> List[Paper]:
        """Runs the full NLP pipeline on a set of papers."""
        for paper in papers:
            text_to_analyze = f"{paper.title}. {paper.abstract if paper.abstract else ''}"
            paper.language = self.detect_language(text_to_analyze)
            paper.classification = self.classify_paper(paper)
            
        return self.calculate_similarity(query, papers)
