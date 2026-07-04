import sys
from adapters.repository.sqlite_cache import SQLiteCache
from infrastructure.nlp_tools.processor import NLPProcessor
from use_cases.ranking_engine import RankingEngine
from adapters.search_gateways.arxiv import ArxivClient
from adapters.search_gateways.semantic_scholar import SemanticScholarClient
from adapters.search_gateways.scholar import ScholarClient
from use_cases.search_interactor import SearchInteractor

def run_test():
    cache = SQLiteCache()
    nlp = NLPProcessor()
    ranking = RankingEngine()
    clients = [ArxivClient()]  # just arxiv to be fast
    
    interactor = SearchInteractor(clients, cache, nlp, ranking)
    
    print("Executing search for 'machine learning'...")
    results = interactor.execute_search("machine learning", max_results=2, year_start=2023)
    
    print(f"Found {len(results)} results")
    for r in results:
        print(f"[{r.final_score}] {r.title}")
        
if __name__ == "__main__":
    run_test()
