import os
import json
import logging
import argparse
import re
from typing import List, Dict, Any

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

from rank_bm25 import BM25Okapi  # pip install rank_bm25

# --- Setup logging ------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- NLTK data download (once) -----------------------
for pkg in ("punkt", "stopwords"):
    try:
        nltk.data.find(f"tokenizers/{pkg}") if pkg == "punkt" else nltk.data.find(f"corpora/{pkg}")
    except LookupError:
        nltk.download(pkg)

# --- Text preprocessing helper -----------------------
class TextPreprocessor:
    def __init__(self):
        self.stop_words = set(stopwords.words("english"))
        self.stemmer = PorterStemmer()
        # only keep letters & numbers
        self.clean_re = re.compile(r"[^\w\s]")

    def tokenize(self, text: str) -> List[str]:
        text = text or ""
        text = self.clean_re.sub("", text.lower())
        tokens = word_tokenize(text)
        return [
            self.stemmer.stem(tok)
            for tok in tokens
            if tok not in self.stop_words and tok.isalpha()
        ]

# --- BM25 matcher ------------------------------------
class YCCompanyMatcher:
    def __init__(self, data_path: str):
        self.data_path = data_path
        self.processor = TextPreprocessor()
        self._load_data()
        self._build_index()

    def _load_data(self) -> None:
        if not os.path.isfile(self.data_path):
            logging.error(f"Data file not found: {self.data_path}")
            raise FileNotFoundError(self.data_path)

        with open(self.data_path, "r", encoding="utf-8") as f:
            self.companies: List[Dict[str, Any]] = json.load(f)
        logging.info(f"Loaded {len(self.companies)} companies from {self.data_path}")

    def _build_index(self) -> None:
        # combine and preprocess each company’s text
        self.docs = []
        for comp in self.companies:
            raw = " ".join([
                comp.get("name", ""),
                comp.get("blurb", ""),
                comp.get("description", ""),
            ])
            tokens = self.processor.tokenize(raw)
            self.docs.append(tokens)

        # build BM25
        self.bm25 = BM25Okapi(self.docs)
        logging.info("BM25 index built.")

    def match(self, query: str, top_n: int = 5) -> List[Dict[str, Any]]:
        q_tokens = self.processor.tokenize(query)
        scores = self.bm25.get_scores(q_tokens)
        top_idxs = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]

        results = []
        for idx in top_idxs:
            comp = self.companies[idx].copy()
            comp["relevance_score"] = float(scores[idx])
            results.append(comp)
        return results

# --- CLI ---------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Find top-N most relevant YC companies to a query via BM25"
    )
    parser.add_argument(
        "--data-file",
        type=str,
        default="data/company_details.json",
        help="Path to the scraped company details JSON"
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="Text to match against the company dataset"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of top results to return"
    )
    args = parser.parse_args()

    matcher = YCCompanyMatcher(args.data_file)
    top_companies = matcher.match(args.query, args.top_n)

    for rank, comp in enumerate(top_companies, start=1):
        print(f"{rank}. {comp['name']} (Score: {comp['relevance_score']:.4f})")
        print(f"   Blurb: {comp.get('blurb', 'N/A')}\n")

if __name__ == "__main__":
    main()