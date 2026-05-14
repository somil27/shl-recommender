"""BM25 search implementation"""
from rank_bm25 import BM25Okapi
import json

class BM25SearchEngine:
    def __init__(self, catalog_path="data/assessments.json"):
        with open(catalog_path, 'r') as f:
            self.catalog = json.load(f)
        
        # Build BM25 index
        documents = [
            f"{a['name']} {a['description']} {' '.join(a['skills'])}"
            for a in self.catalog
        ]
        self.bm25 = BM25Okapi([doc.split() for doc in documents])
    
    def search(self, query: str, top_k: int = 10):
        """Search assessments"""
        scores = self.bm25.get_scores(query.split())
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [self.catalog[i] for i in top_indices]

# Initialize on startup
search_engine = BM25SearchEngine()