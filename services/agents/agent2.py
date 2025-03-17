import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
import asyncio
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.feature_extraction.text import TfidfVectorizer
import time

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from langgraph.prebuilt import tools_condition, ToolNode
from typing import Dict, Any
from config import config
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.chat_models import init_chat_model
from langgraph.graph import START, MessagesState, StateGraph
from tools.get_schema import get_schema
from tools.execute_sql import execute_sql_query
from tools.query_data_dictionary import get_db_field_definition
from langgraph.checkpoint.memory import MemorySaver

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
        self.memory = MemorySaver()
        
        self.llm = init_chat_model(
            config.llm_config['model'],
            temperature=config.llm_config['temperature'],
            max_tokens=config.llm_config['max_tokens'],
            streaming=config.llm_config['streaming']
        )
        
        self.tools = [get_schema, execute_sql_query, get_db_field_definition]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.setup_graph()
        self.ground_truth_path = Path(__file__).parent.parent.parent / config.evaluation_config['ground_truth_path']

    def setup_graph(self):
        # Define the system message and tools
        # Define system message with clear tool descriptions and instructions
        sys_msg = SystemMessage(
            content="You are a SQL assistant that helps users query databases. "
               "You can use the following tools: "
               "1. get_schema: Get database structure "
               "2. execute_sql_query: Run SQL queries "
               "3. get_data_dictionary: Get data dictionary. "
               "Check the produced sql query for correctness. And fix if not working. "
               "Always provide accurate and concise information. "
               "Always provide sql queries when you cheked its wotking. "
               "I dont want you to provide answers, I want you to provide just pure sql queries. "
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
        
        self.graph = builder.compile(checkpointer=self.memory)

    async def process_query(self, query: str) -> str:
        messages = [HumanMessage(content=query)]
        config = {"configurable": {"thread_id": 1}}
        result = await self.graph.ainvoke({"messages": messages},config)
        return result['messages'][-1].content

    async def evaluate_performance(self, num_queries: int = None) -> Dict[str, Any]:
        """
        Evaluates the SQL assistant's performance against ground truth data.
        
        Args:
            num_queries (int, optional): Number of queries to evaluate. If None, evaluates all queries.
            
        Returns:
            Dict[str, Any]: Dictionary containing performance metrics
        """
        # Load ground truth data
        try:
            df = pd.read_csv(self.ground_truth_path)
            if num_queries:
                df = df.head(num_queries)
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
            "failed_cases": [],
            "execution_time": 0.0
        }

        start_time = time.time()

        for idx, row in df.iterrows():
            try:
                # Get assistant's SQL query
                assistant_result = await self.process_query(row["User Input"])
                
                # Extract SQL query from assistant's response
                # Look for SQL query in the response - it could be in different formats
                assistant_sql = ""
                response_lower = assistant_result.lower()
                
                # Common patterns to identify SQL in response
                sql_markers = ["select", "insert", "update", "delete", "with"]
                for line in response_lower.split('\n'):
                    line = line.strip()
                    if any(line.startswith(marker) for marker in sql_markers):
                        assistant_sql = line
                        break
                
                if not assistant_sql:
                    # If no SQL found, try to extract code block if present
                    if "```sql" in response_lower:
                        sql_block = response_lower.split("```sql")[1].split("```")[0]
                        assistant_sql = sql_block.strip()
                    elif "```" in response_lower:
                        sql_block = response_lower.split("```")[1].split("```")[0]
                        assistant_sql = sql_block.strip()

                ground_truth_sql = row["Ground Truth SQL"].lower().strip()

                # Calculate similarity
                if assistant_sql and ground_truth_sql:
                    tfidf_matrix = vectorizer.fit_transform([assistant_sql, ground_truth_sql])
                    similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
                    
                    results["similarities"].append({
                        "query_id": idx + 1,
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
                            "query_id": idx + 1,
                            "query": row["User Input"],
                            "assistant_sql": assistant_sql,
                            "ground_truth_sql": ground_truth_sql,
                            "similarity": similarity
                        })
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

        # Calculate statistics
        results["execution_time"] = time.time() - start_time
        if results["similarities"]:
            similarities = [s["similarity"] for s in results["similarities"]]
            results["average_similarity"] = np.mean(similarities)
            results["median_similarity"] = np.median(similarities)
            results["min_similarity"] = np.min(similarities)
            results["max_similarity"] = np.max(similarities)
            results["success_rate"] = (results["successful_queries"] / results["total_queries"]) * 100

        return results

async def main():
    assistant = SQLQueryAssistant()
    
    print("\n=== SQL Query Assistant Chatbot ===")
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'help' for command list")
    print("===================================\n")

    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Handle exit commands
            if user_input.lower() in ['exit', 'quit']:
                print("\nGoodbye! Thanks for using SQL Query Assistant.")
                break
                
            # Handle help command    
            if user_input.lower() == 'help':
                print("\nAvailable commands:")
                print("- exit/quit: End the conversation")
                print("- help: Show this help message")
                print("- clear: Clear the screen")
                print("- eval: Run performance evaluation")
                continue
                
            # Handle clear command
            if user_input.lower() == 'clear':
                os.system('cls' if os.name == 'nt' else 'clear')
                continue
                
            # Handle evaluation command    
            if user_input.lower().startswith('eval'):
                print("\nRunning performance evaluation...")
                # Parse number of queries if provided (eval 5)
                num_queries = None
                if len(user_input.split()) > 1:
                    try:
                        num_queries = int(user_input.split()[1])
                    except ValueError:
                        print("Invalid number of queries specified")
                        continue
                
                eval_results = await assistant.evaluate_performance(num_queries)
                print("\n=== Evaluation Summary ===")
                print(f"Total queries evaluated: {eval_results['total_queries']}")
                print(f"Successful queries: {eval_results['successful_queries']}")
                print(f"Failed queries: {eval_results['failed_queries']}")
                print(f"Success rate: {eval_results.get('success_rate', 0):.2f}%")
                print(f"Average similarity: {eval_results.get('average_similarity', 0):.2f}")
                print(f"Execution time: {eval_results['execution_time']:.2f} seconds")
                
                print("\n=== Detailed Results ===")
                # Print successful cases
                if eval_results['similarities']:
                    print("\nSuccessful Cases:")
                    for case in eval_results['similarities']:
                        if case['similarity'] >= config.evaluation_config.get('similarity_threshold', 0.8):
                            print("\n" + "="*50)
                            print(f"Query {case['query_id']}: {case['query']}")
                            print("\nGround Truth SQL:")
                            print(case['ground_truth_sql'])
                            print("\nAssistant SQL:")
                            print(case['assistant_sql'])
                            print(f"Similarity Score: {case['similarity']:.2f}")
                
                # Print failed cases
                if eval_results['failed_cases']:
                    print("\nFailed Cases:")
                    for case in eval_results['failed_cases']:
                        print("\n" + "="*50)
                        print(f"Query {case['query_id']}: {case['query']}")
                        if 'error' in case:
                            print(f"Error: {case['error']}")
                        else:
                            print("\nGround Truth SQL:")
                            print(case['ground_truth_sql'])
                            print("\nAssistant SQL:")
                            print(case['assistant_sql'])
                            print(f"Similarity Score: {case['similarity']:.2f}")
                
                print("\n" + "="*50)
                continue
            
            # Process regular queries
            if user_input:
                print("\nAssistant: ", end="")
                try:
                    result = await assistant.process_query(user_input)
                    print(result)
                except Exception as e:
                    print(f"Sorry, I encountered an error: {str(e)}")
            
            print() # Add blank line for readability
            
        except KeyboardInterrupt:
            print("\n\nGoodbye! Thanks for using SQL Query Assistant.")
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {str(e)}")
            print("Please try again.")

if __name__ == "__main__":
    asyncio.run(main())
