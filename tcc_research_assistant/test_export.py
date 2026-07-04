import sys
from adapters.exporters.pdf_export import PDFExporter
from adapters.exporters.excel_export import ExcelExporter
from core.entities import Paper

def run_test():
    papers = [
        Paper(
            title="Test Paper 1",
            authors=["John Doe", "Jane Doe"],
            year=2023,
            abstract="This is a test abstract.",
            url="http://example.com/1",
            source="MockSource",
            citations=10,
            final_score=0.95
        ),
        Paper(
            title="Test Paper 2",
            authors=["Alice", "Bob"],
            year=2024,
            abstract="This is another test abstract.",
            url="http://example.com/2",
            source="MockSource",
            citations=5,
            final_score=0.88
        )
    ]
    
    print("Exporting PDF...")
    pdf_exp = PDFExporter()
    pdf_path = pdf_exp.export(papers, "test_output.pdf")
    print(f"PDF exported to: {pdf_path}")
    
    print("Exporting Excel...")
    excel_exp = ExcelExporter()
    xlsx_path = excel_exp.export(papers, "test_output.xlsx")
    print(f"Excel exported to: {xlsx_path}")

if __name__ == "__main__":
    run_test()
