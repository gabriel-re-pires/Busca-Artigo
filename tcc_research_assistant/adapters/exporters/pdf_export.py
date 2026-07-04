from typing import List
from core.entities import Paper
from adapters.exporters.base_exporter import BaseExporter
import os

try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

class PDFExporter(BaseExporter):
    def export(self, papers: List[Paper], filepath: str) -> str:
        if FPDF is None:
            # Fallback to text if fpdf2 is not installed
            filepath = filepath.replace('.pdf', '.txt')
            with open(filepath, 'w', encoding='utf-8') as f:
                for idx, p in enumerate(papers, 1):
                    f.write(f"[{idx}] {p.title}\n")
                    f.write(f"Score: {p.final_score} | Sim: {p.similarity_score} | Year: {p.year}\n")
                    f.write(f"Authors: {', '.join(p.authors)}\n")
                    f.write(f"Source: {p.source} | URL: {p.url}\n")
                    f.write(f"Abstract: {p.abstract[:300]}...\n")
                    f.write("-" * 50 + "\n")
            return filepath

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        
        pdf.set_font("helvetica", style="B", size=16)
        pdf.cell(0, 10, "Busca-Artigo - Resultados", new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.ln(5)

        for idx, p in enumerate(papers, 1):
            pdf.set_font("helvetica", style="B", size=12)
            # Encode correctly to avoid FPDF character errors
            title = f"{idx}. {p.title}".encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 8, title)
            
            pdf.set_font("helvetica", size=10)
            meta = f"Score: {p.final_score} | Similarity: {p.similarity_score} | Citations: {p.citations} | Year: {p.year}"
            pdf.cell(0, 6, meta.encode('latin-1', 'replace').decode('latin-1'), new_x="LMARGIN", new_y="NEXT")
            
            authors_str = ", ".join(p.authors) if p.authors else "Unknown Authors"
            pdf.cell(0, 6, f"Authors: {authors_str}".encode('latin-1', 'replace').decode('latin-1'), new_x="LMARGIN", new_y="NEXT")
            
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 6, f"Source: {p.source} | URL: {p.url}".encode('latin-1', 'replace').decode('latin-1'), new_x="LMARGIN", new_y="NEXT")
            pdf.set_text_color(0, 0, 0)
            
            if p.abstract:
                pdf.ln(2)
                pdf.set_font("helvetica", style="I", size=9)
                abstract_text = f"Abstract: {p.abstract[:500]}..." if len(p.abstract) > 500 else f"Abstract: {p.abstract}"
                pdf.multi_cell(0, 5, abstract_text.encode('latin-1', 'replace').decode('latin-1'))
            
            pdf.ln(8)

        pdf.output(filepath)
        return filepath
