import pandas as pd
import numpy as np
from pathlib import Path
import time
from typing import Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

from config import config

class SQLEvaluationService:
    def __init__(self):
        self.ground_truth_path = Path(__file__).parent.parent / config.evaluation_config['ground_truth_path']
        self.vectorizer = TfidfVectorizer(lowercase=True, strip_accents='unicode')
    
    def extract_sql_from_response(self, response: str) -> str:
        """Extract SQL query from assistant's response"""
        response_lower = response.lower()
        assistant_sql = ""
        
        # Check for SQL keywords
        sql_markers = ["select", "insert", "update", "delete", "with"]
        for line in response_lower.split('\n'):
            line = line.strip()
            if any(line.startswith(marker) for marker in sql_markers):
                assistant_sql = line
                break
        
        # If no SQL found, try code blocks
        if not assistant_sql:
            if "```sql" in response_lower:
                sql_block = response_lower.split("```sql")[1].split("```")[0]
                assistant_sql = sql_block.strip()
            elif "```" in response_lower:
                sql_block = response_lower.split("```")[1].split("```")[0]
                assistant_sql = sql_block.strip()
                
        return assistant_sql

    async def evaluate_assistant(self, assistant, num_queries: Optional[int] = None) -> Dict[str, Any]:
        """
        Evaluates SQL assistant's performance against ground truth data.
        
        Args:
            assistant: SQL assistant instance with process_query method
            num_queries: Number of queries to evaluate. If None, evaluates all queries.
            
        Returns:
            Dict[str, Any]: Evaluation metrics and results
        """
        try:
            df = pd.read_csv(self.ground_truth_path)
            if num_queries:
                df = df.head(num_queries)
        except Exception as e:
            return {"error": f"Failed to load ground truth data: {str(e)}"}

        results = {
            "total_queries": len(df),
            "successful_queries": 0,
            "failed_queries": 0,
            "average_similarity": 0.0,
            "similarities": [],
            "failed_cases": [],
            "execution_time": 0.0
        }

        start_time = time.time()

        for idx, row in df.iterrows():
            try:
                assistant_result = await assistant.process_query(row["User Input"])
                assistant_sql = self.extract_sql_from_response(assistant_result)
                ground_truth_sql = row["Ground Truth SQL"].lower().strip()

                if assistant_sql and ground_truth_sql:
                    tfidf_matrix = self.vectorizer.fit_transform([assistant_sql, ground_truth_sql])
                    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                    
                    case_data = {
                        "query_id": idx + 1,
                        "query": row["User Input"],
                        "similarity": similarity,
                        "assistant_sql": assistant_sql,
                        "ground_truth_sql": ground_truth_sql
                    }
                    
                    results["similarities"].append(case_data)
                    
                    if similarity >= config.evaluation_config.get('similarity_threshold', 0.8):
                        results["successful_queries"] += 1
                    else:
                        results["failed_queries"] += 1
                        results["failed_cases"].append(case_data)
                else:
                    results["failed_queries"] += 1
                    results["failed_cases"].append({
                        "query_id": idx + 1,
                        "query": row["User Input"],
                        "error": "No SQL query found in response"
                    })
                    
            except Exception as e:
                results["failed_queries"] += 1
                results["failed_cases"].append({
                    "query_id": idx + 1,
                    "query": row["User Input"],
                    "error": str(e)
                })

        results["execution_time"] = time.time() - start_time
        
        if results["similarities"]:
            similarities = [s["similarity"] for s in results["similarities"]]
            results["average_similarity"] = np.mean(similarities)
            results["median_similarity"] = np.median(similarities)
            results["min_similarity"] = np.min(similarities)
            results["max_similarity"] = np.max(similarities)
            results["success_rate"] = (results["successful_queries"] / results["total_queries"]) * 100

        return results
