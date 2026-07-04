from typing import List
from core.entities import Paper
import langdetect
import logging

class FilterEngine:
    def __init__(self):
        # Prevent langdetect from crashing if seed is not initialized
        langdetect.DetectorFactory.seed = 0

    def detect_language(self, paper: Paper) -> str:
        """
        Detects the language of a paper based on its title and abstract.
        Returns 'Português', 'Inglês', or 'Outro'.
        """
        text_to_detect = f"{paper.title} {paper.abstract}".strip()
        if not text_to_detect:
            return "Outro"

        try:
            detected_code = langdetect.detect(text_to_detect)
            if detected_code in ['pt', 'pt-br']:
                return "Português"
            elif detected_code == 'en':
                return "Inglês"
            else:
                return "Outro"
        except Exception as e:
            logging.error(f"Language detection failed for paper '{paper.title}': {e}")
            return "Outro"

    def filter_papers(self, papers: List[Paper], lang_pref: str, year_start: int = None, year_end: int = None) -> List[Paper]:
        """
        Applies year and language filters to the list of papers.
        """
        filtered = []
        for paper in papers:
            # 1. Year filter
            if paper.year is not None:
                if year_start is not None and paper.year < year_start:
                    continue
                if year_end is not None and paper.year > year_end:
                    continue
            else:
                # If the paper doesn't have a year, it passes the year filter or fails?
                # Usually we let it pass, or we could strict filter. Let's let it pass if year is unknown,
                # or maybe strict filter. The user said: "If empty, ignore the filter."
                # It means if the input is empty, don't filter.
                # If paper has no year, but filter is active, we might drop it or keep it.
                # Let's keep it if we want to be permissive. Or skip it. We'll skip it if it strictly violates.
                # Actually, if paper.year is None but filter is set, it's safer to skip if we want strictly those years.
                if year_start is not None or year_end is not None:
                    continue  

            # 2. Language filter
            # First, check/detect language if not set
            if paper.language == "unknown":
                paper.language = self.detect_language(paper)

            if lang_pref != "Todos":
                if paper.language != lang_pref:
                    continue

            filtered.append(paper)

        return filtered
