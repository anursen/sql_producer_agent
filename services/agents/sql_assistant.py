import sqlite3
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)

from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import START, END, Graph
from typing import Dict, Any
from config import config
import yaml
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent.parent.parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


class SQLQueryAssistant:
    def __init__(self, db_path=None):
        self.db_path = db_path or config.database_config['default_path']
        
        self.llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.llm_config['model'],
            temperature=config.llm_config['temperature'],
            max_tokens=config.llm_config['max_tokens'],
            streaming=config.llm_config['streaming']
        )
        
        self.db = SQLDatabase.from_uri(f"sqlite:///{self.db_path}")
        self.setup_graph()



    def setup_graph(self):
        def generate_sql(state: Dict[str, Any]):
            query = state["query"]
            template = """Given the following SQL tables, write a SQL query to answer the user's question.
            Question: {question}
            SQL Query:"""
            prompt = ChatPromptTemplate.from_template(template)
            chain = prompt | self.llm | StrOutputParser()
            sql_query = chain.invoke({"question": query})
            state["sql"] = sql_query
            return state

        def execute_query(state: Dict[str, Any]):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                results = cursor.execute(state["sql"]).fetchall()
                state["results"] = results
            except Exception as e:
                state["error"] = str(e)
            finally:
                conn.close()
            return state

        workflow = Graph()
        workflow.add_edge(START,'generate_sql')
        workflow.add_node("generate_sql", generate_sql)
        workflow.add_node("execute_query", execute_query)
        workflow.add_edge("generate_sql", "execute_query")
        workflow.add_edge("execute_query", END)

        self.graph = workflow.compile()

    def process_query(self, query: str) -> Dict[str, Any]:
        result = self.graph.invoke({"query": query})
        return result

def main():
    # Create an instance of SQLQueryAssistant
    assistant = SQLQueryAssistant()
    
    # Test query
    test_input = "Show me all tables in the database"
    print(f"Testing query: {test_input}")
    
    # Process the query
    try:
        result = assistant.process_query(test_input)
        print("\nQuery Results:")
        print("SQL Query:", result.get("sql"))
        print("Results:", result.get("results"))
        if "error" in result:
            print("Error:", result["error"])
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()
