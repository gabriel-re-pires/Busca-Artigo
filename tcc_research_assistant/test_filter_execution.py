import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infrastructure.nlp_tools.processor import NLPProcessor
from use_cases.ranking_engine import RankingEngine
from adapters.repository.sqlite_cache import SQLiteCache
from adapters.search_gateways.arxiv import ArxivClient
from use_cases.search_interactor import SearchInteractor

def test_filters():
    interactor = SearchInteractor(
        clients=[ArxivClient()],
        cache=SQLiteCache(),
        nlp=NLPProcessor(),
        ranking=RankingEngine()
    )
    
    print("Test 1: Normal Search")
    res1 = interactor.execute_search("machine learning", max_results=3, lang_pref="Todos")
    for r in res1:
        print(f"[{r.language}] {r.year} - {r.title}")
        
    print("\nTest 2: Filter by Year (2020-2022)")
    res2 = interactor.execute_search("machine learning", max_results=3, year_start=2020, year_end=2022)
    for r in res2:
        print(f"[{r.language}] {r.year} - {r.title}")
        
    print("\nTest 3: Filter by Language (Português)")
    # Since arXiv is mostly English, it might not find any or it might detect some as Outro/Português incorrectly.
    res3 = interactor.execute_search("aprendizado de máquina", max_results=3, lang_pref="Português")
    for r in res3:
        print(f"[{r.language}] {r.year} - {r.title}")

if __name__ == "__main__":
    test_filters()
