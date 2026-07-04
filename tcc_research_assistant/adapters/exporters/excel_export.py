import urllib.parse
from typing import List
from core.entities import Paper
from adapters.exporters.base_exporter import BaseExporter
import pandas as pd

class ExcelExporter(BaseExporter):
    def export(self, papers: List[Paper], filepath: str) -> str:
        data = []
        for i, p in enumerate(papers, 1):
            data.append({
                '#': i,
                'Score': p.final_score,
                'Similarity': p.similarity_score,
                'Title': p.title,
                'Authors': ", ".join(p.authors),
                'Year': p.year,
                'Source': p.source,
                'Citations': p.citations,
                'Classification': p.classification,
                'Language': p.language,
                'Abstract': p.abstract,
                'URL': p.url,
                'DOI': p.doi,
                'Related Discovered': ", ".join(p.related_papers) if p.related_papers else "None"
            })
            
        df = pd.DataFrame(data)
        try:
            # Requires openpyxl installed
            df.to_excel(filepath, index=False, engine='openpyxl')
        except Exception as e:
            # Fallback to CSV if openpyxl fails
            filepath = filepath.replace('.xlsx', '.csv')
            df.to_csv(filepath, index=False)
            
        return filepath
