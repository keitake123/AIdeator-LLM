import os
import json
import logging
import re
from typing import List, Dict, Any, Optional

# Import NLTK components
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer

# Import BM25 for relevancy matching
from rank_bm25 import BM25Okapi

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("StartupRelevancyMatcher")

# --- NLTK data download (once) -----------------------
for pkg, path in [
    ("punkt",       "tokenizers/punkt"),
    ("stopwords",   "corpora/stopwords"),
]:
    try:
        nltk.data.find(path)
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
class StartupMatcher:
    def __init__(self, 
                 yc_data_path: str = "data/company_details.json", 
                 ph_data_path: str = "data/producthunt_all_years.json"):
        self.yc_data_path = yc_data_path
        self.ph_data_path = ph_data_path
        self.processor = TextPreprocessor()
        self._load_data()
        self._build_index()

    def _load_data(self) -> None:
        # Initialize companies list
        self.companies = []
        
        # Load YC data
        if os.path.isfile(self.yc_data_path):
            try:
                with open(self.yc_data_path, "r", encoding="utf-8") as f:
                    yc_companies = json.load(f)
                
                # Ensure each company has a source field
                for company in yc_companies:
                    company['source'] = company.get('source', 'yc')
                
                self.companies.extend(yc_companies)
                logging.info(f"Loaded {len(yc_companies)} YC companies from {self.yc_data_path}")
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON from {self.yc_data_path}")
        else:
            logging.warning(f"YC data file not found: {self.yc_data_path}")
        
        # Load ProductHunt data
        if os.path.isfile(self.ph_data_path):
            try:
                with open(self.ph_data_path, "r", encoding="utf-8") as f:
                    ph_data = json.load(f)
                    
                # ProductHunt data is stored by year, flatten it
                ph_companies = []
                for year, companies in ph_data.items():
                    for company in companies:
                        # Ensure source field
                        company['source'] = company.get('source', 'producthunt')
                        ph_companies.append(company)
                
                self.companies.extend(ph_companies)
                logging.info(f"Loaded {len(ph_companies)} ProductHunt products from {self.ph_data_path}")
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON from {self.ph_data_path}")
        else:
            logging.warning(f"ProductHunt data file not found: {self.ph_data_path}")
        
        # Check if we have any data to work with
        if not self.companies:
            logging.error("No company data found in either source")
            raise FileNotFoundError("No company data available")
            
        logging.info(f"Combined dataset contains {len(self.companies)} companies/products")

    def _build_index(self) -> None:
        # combine and preprocess each company's text
        self.docs = []
        for comp in self.companies:
            # Check for different field names that might exist
            name = comp.get("name", comp.get("title", ""))
            blurb = comp.get("blurb", "")
            description = comp.get("description", "")
            
            # For ProductHunt data, we might have 'features' as a list
            features = ""
            if isinstance(comp.get("features", ""), list):
                features = " ".join(comp.get("features", []))
            
            raw = " ".join([name, blurb, description, features])
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

    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """Format the results as a nice string for display."""
        if not results:
            return "No relevant companies found."
            
        output = "### Top Similar Startups\n\n"
        for rank, comp in enumerate(results, start=1):
            # Extract fields with fallbacks for different field names
            name = comp.get("name", comp.get("title", "Unknown"))
            blurb = comp.get("blurb", "N/A")
            description = comp.get("description", "N/A")
            logo_url = comp.get("logo_url", comp.get("profile_picture", "N/A"))
            url = comp.get("url", "N/A")
            score = comp.get("relevance_score", 0.0)
            source = comp.get("source", "unknown")
            
            output += f"**{rank}. {name}** (Relevance: {score:.2f}, Source: {source})\n"
            
            # Add profile picture link (before the blurb)
            if logo_url != "N/A":
                output += f"Profile Picture: {logo_url}\n"
                
            # Add fields without bold formatting
            output += f"Blurb: {blurb}\n"
            output += f"Description: {description[:150]}{'...' if len(description) > 150 else ''}\n"
            
            if url != "N/A":
                output += f"URL: {url}\n"
                
            output += "\n"
        
        return output


# --- Integration with ideation_graph.py --------------
def find_relevant_companies(product_idea: Dict[str, Any], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Take a product idea dictionary and find relevant startups from both YC and ProductHunt.
    
    Args:
        product_idea: A dictionary containing product idea details
        top_n: Number of top matches to return
        
    Returns:
        List of relevant companies with relevance scores
    """
    # Initialize the matcher
    try:
        matcher = StartupMatcher()
    except Exception as e:
        logging.error(f"Failed to initialize startup matcher: {e}")
        return []
    
    # Extract relevant text from product idea
    query_parts = []
    
    # Check for various fields that might exist in product ideas
    if "heading" in product_idea:
        query_parts.append(product_idea["heading"])
    
    # Handle different field names used in different branch categories
    if product_idea.get("category") == "product":
        # Product category fields
        if "description" in product_idea:
            query_parts.append(product_idea["description"])
        
        # Include features if available
        features = product_idea.get("features", [])
        if features:
            if isinstance(features, list):
                query_parts.append(" ".join(features))
            else:
                query_parts.append(features)
    else:
        # Concept category fields
        if "explanation" in product_idea:
            query_parts.append(product_idea["explanation"])
        if "productDirection" in product_idea:
            query_parts.append(product_idea["productDirection"])
    
    # Build the query text
    query_text = " ".join(query_parts)
    
    # If we couldn't extract any meaningful text, return empty list
    if not query_text.strip():
        logging.warning("No valid text extracted from product idea for relevancy matching")
        return []
    
    # Log the query being used
    logging.info(f"Finding relevant companies for: {query_text[:100]}...")
    
    # Perform the matching
    try:
        return matcher.match(query_text, top_n)
    except Exception as e:
        logging.error(f"Error matching companies: {e}")
        return []

# Add a function to display formatted results in terminal
def display_search_results(results, branch_heading):
    """
    Display search results for similar startups in a formatted way.
    
    Args:
        results: List of company results from relevancy search
        branch_heading: Heading of the branch that was searched
    """
    if not results:
        print("\n===== NO SIMILAR COMPANIES FOUND =====")
        print(f"No companies similar to '{branch_heading}' were found.")
        print("=" * 40)
        return
    
    print("\n" + "=" * 80)
    print(f"===== SIMILAR STARTUPS TO: {branch_heading} =====")
    print("=" * 80)
    
    for i, company in enumerate(results, 1):
        # Extract company details with fallbacks for different field names
        name = company.get("name", company.get("title", "Unknown"))
        blurb = company.get("blurb", "N/A")
        description = company.get("description", "N/A")
        logo_url = company.get("logo_url", company.get("profile_picture", "N/A"))
        url = company.get("url", "N/A")
        score = company.get("relevance_score", 0.0)
        source = company.get("source", "unknown").upper()
        
        # Print company details with formatting
        print(f"\n{i}. {name} (Relevance Score: {score:.2f}, Source: {source})")
        print("-" * 50)
        
        # Show logo URL if available
        if logo_url != "N/A":
            print(f"Profile Picture: {logo_url}")
        
        # Show company URL if available
        if url != "N/A":
            print(f"URL: {url}")
        
        # Show blurb with line wrapping
        if blurb != "N/A":
            print(f"\nBlurb: {blurb}")
        
        # Show description with truncation for readability
        if description != "N/A":
            max_desc_len = 200
            desc_display = description[:max_desc_len] + "..." if len(description) > max_desc_len else description
            print(f"\nDescription: {desc_display}")
        
        print("-" * 50)
    
    print("=" * 80)
    print("\n")