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
               "If user is asking for result provide the result from the database. "
               "otherwise provide the SQL query."
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

    async def evaluate_performance(self) -> Dict[str, Any]:
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
                assistant_result = await self.process_query(row["User Input"])
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
            if user_input.lower() == 'eval':
                print("\nRunning performance evaluation...")
                eval_results = await assistant.evaluate_performance()
                print("\nEvaluation results:", eval_results)
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
