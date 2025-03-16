import sqlite3
from pathlib import Path
from langchain_core.tools import tool
import sys

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from config import config

@tool
def execute_sql_query(query: str, db_path: str = None) -> dict:
    """
    Execute a SQL query on the specified database.
    
    Args:
        query: The SQL query to execute
        db_path: Optional path to the database file. If not provided, uses default from config
        
    Returns:
        dict: Contains either 'results' with query results or 'error' with error message
        
    Example:
        >>> result = execute_sql_query("SELECT * FROM customers LIMIT 5")
        >>> print(result)
        {'results': [(1, 'John', 'Doe'), (2, 'Jane', 'Smith'), ...]}
    """
    try:
        if not db_path:
            db_path = Path(__file__).parent.parent / config.database_config['default_path']
            print(f"Using database: {db_path}")
            
        if not Path(db_path).exists():
            return {"error": f"Database file not found: {db_path}"}
            
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            results = cursor.fetchall()
            
            # Get column names
            column_names = [description[0] for description in cursor.description] if cursor.description else []
            
            print(f"[TOOL][Api call] => execute_sql_query(query={query})")
            return {
                "results": results,
                "columns": column_names,
                "row_count": len(results)
            }
            
    except Exception as e:
        return {"error": str(e)}

def main():
    """Interactive test function for SQL query execution"""
    print("SQL Query Executor")
    print("----------------")
    print("Enter 'exit' to quit\n")
    
    while True:
        query = input("Enter SQL query: ").strip()
        if query.lower() == 'exit':
            break
            
        result = execute_sql_query(query)
        print("\nResults:")
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Columns: {result['columns']}")
            print("Data:")
            for row in result['results']:
                print(row)
            print(f"\nTotal rows: {result['row_count']}")
        print("----------------\n")

if __name__ == "__main__":
    main()
