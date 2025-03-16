import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from langgraph.graph import START, StateGraph
from langgraph.prebuilt import tools_condition, ToolNode
from typing import Dict, Any, List
from config import config
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.chat_models import init_chat_model


@tool("get_schema")
def get_schema(database_path: str) -> str:
    """Get the database schema information"""
    # Placeholder for schema retrieval logic
    pass

@tool("execute_sql_query")
def execute_sql_query(query: str, database_path: str) -> List[tuple]:
    """Execute the given SQL query and return results"""
    # Placeholder for query execution logic
    pass

@tool("get_table_details")
def get_table_details(table_name: str, database_path: str) -> str:
    """Get detailed information about a specific table"""
    # Placeholder for table details logic
    pass

class SQLQueryAssistant:
    '''We need to redefine graph again.
    It should use execute_query and get_schema_info functions as tools
    these functions are running local and not consumpting tokens.
    so they can be used as required without any constraint.
    generate_sql function will be a llm call and llm will anayze which toll to 
    use or output the response.
    '''
    
    def __init__(self, db_path=None):
        self.db_path = db_path or config.database_config['default_path']
        
        self.llm = init_chat_model(
            config.llm_config['model'],
            temperature=config.llm_config['temperature'],
            max_tokens=config.llm_config['max_tokens'],
            streaming=config.llm_config['streaming']
        )
        
        self.tools = [get_schema, execute_sql_query, get_table_details]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.setup_graph()
        self.ground_truth_path = Path(__file__).parent.parent.parent / config.evaluation_config['ground_truth_path']

    def setup_graph(self):
        sys_msg = SystemMessage(
            content="You are a SQL assistant that helps users query databases. "
                   "You can use the following tools: "
                   "1. get_schema: Get database structure "
                   "2. execute_sql_query: Run SQL queries "
                   "3. get_table_details: Get detailed table information "
                   "Always provide accurate and helpful responses."
        )
        
        async def assistant(state: MessagesState):
            return {"messages": [await self.llm_with_tools.ainvoke([sys_msg] + state["messages"])]}

        # Graph
        builder = StateGraph(MessagesState)
        
        # Define nodes
        builder.add_node("assistant", assistant)
        builder.add_node("tools", ToolNode(self.tools))
        
        # Define edges
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges(
            "assistant",
            tools_condition,
        )
        builder.add_edge("tools", "assistant")
        
        self.graph = builder.compile()

    async def process_query(self, query: str) -> str:
        messages = [HumanMessage(content=query)]
        result = await self.graph.ainvoke({"messages": messages})
        return result['messages'][-1].content

    def evaluate_performance(self) -> Dict[str, Any]:
        """
        Evaluates the SQL assistant's performance against ground truth data.
        Returns a dictionary containing performance metrics.
        """
        # Load ground truth data
        try:
            df = pd.read_csv(self.ground_truth_path).head(5)
        except Exception as e:
            return {"error": f"Failed to load ground truth data: {str(e)}"}

        # Initialize vectorizer for cosine similarity
        vectorizer = TfidfVectorizer(lowercase=True, strip_accents='unicode')

        # Store results
        results = {
            "total_queries": len(df),
            "successful_queries": 0,
            "failed_queries": 0,
            "average_similarity": 0.0,
            "similarities": [],
            "failed_cases": []
        }

        for idx, row in df.iterrows():
            try:
                # Get assistant's SQL query
                assistant_result = self.process_query(row["User Input"])
                assistant_sql = assistant_result.get("sql", "").lower().strip()
                ground_truth_sql = row["Ground Truth SQL"].lower().strip()

                # Calculate similarity
                if assistant_sql and ground_truth_sql:
                    tfidf_matrix = vectorizer.fit_transform([assistant_sql, ground_truth_sql])
                    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                    
                    results["similarities"].append({
                        "query": row["User Input"],
                        "similarity": similarity,
                        "assistant_sql": assistant_sql,
                        "ground_truth_sql": ground_truth_sql
                    })
                    
                    if similarity >= config.evaluation_config.get('similarity_threshold', 0.8):
                        results["successful_queries"] += 1
                    else:
                        results["failed_queries"] += 1
                        results["failed_cases"].append({
                            "query": row["User Input"],
                            "assistant_sql": assistant_sql,
                            "ground_truth_sql": ground_truth_sql,
                            "similarity": similarity
                        })
                else:
                    results["failed_queries"] += 1
                    
            except Exception as e:
                results["failed_queries"] += 1
                results["failed_cases"].append({
                    "query": row["User Input"],
                    "error": str(e)
                })

        # Calculate average similarity
        if results["similarities"]:
            results["average_similarity"] = np.mean([s["similarity"] for s in results["similarities"]])

        return results

async def main():
    assistant = SQLQueryAssistant()
    test_input = "Show me all tables in the database"
    print(f"Testing query: {test_input}")
    
    try:
        result = await assistant.process_query(test_input)
        print("\nResponse:", result)
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
