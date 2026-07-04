import sqlite3
import json
from typing import List, Optional
import os
from core.entities import Paper

class SQLiteCache:
    def __init__(self, db_path: str = "research_cache.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS papers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT UNIQUE,
                    authors TEXT,
                    year INTEGER,
                    abstract TEXT,
                    url TEXT,
                    source TEXT,
                    citations INTEGER,
                    language TEXT,
                    classification TEXT,
                    doi TEXT UNIQUE,
                    fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def add_paper(self, paper: Paper) -> bool:
        """Stores a paper in cache. Returns True if inserted, False if duplicate."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO papers (title, authors, year, abstract, url, source, citations, language, classification, doi)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    paper.title,
                    json.dumps(paper.authors),
                    paper.year,
                    paper.abstract,
                    paper.url,
                    paper.source,
                    paper.citations,
                    paper.language,
                    paper.classification,
                    paper.doi
                ))
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Duplicate title or DOI

    def get_paper_by_title(self, title: str) -> Optional[Paper]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM papers WHERE title = ?', (title,))
            row = cursor.fetchone()
            if row:
                return self._row_to_paper(row)
        return None

    def _row_to_paper(self, row) -> Paper:
        return Paper(
            title=row[1],
            authors=json.loads(row[2]) if row[2] else [],
            year=row[3],
            abstract=row[4],
            url=row[5],
            source=row[6],
            citations=row[7],
            language=row[8],
            classification=row[9],
            doi=row[10]
        )

    def deduplicate(self, new_papers: List[Paper]) -> List[Paper]:
        """Filters out papers that already exist in the cache."""
        unique_papers = []
        for paper in new_papers:
            if paper.doi:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT id FROM papers WHERE doi = ?', (paper.doi,))
                    if cursor.fetchone():
                        continue
            
            with sqlite3.connect(self.db_path) as conn:
                 cursor = conn.cursor()
                 cursor.execute('SELECT id FROM papers WHERE title = ?', (paper.title,))
                 if cursor.fetchone():
                     continue
            
            unique_papers.append(paper)
        
        return unique_papers
