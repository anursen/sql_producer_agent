import sqlite3
from pathlib import Path
from langchain_core.tools import tool
import sys
import signal
import json
import csv
from io import StringIO
from langchain_core.tools import tool

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Query execution timed out")

# Add the project root to Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.append(str(project_root))

from config import config

@tool
def execute_sql_query(query: str) -> dict:
    '''
    This function executes a SQL query on a SQLite database with configurable timeout and result limits.
    Results can be returned in different formats (json, csv, or list).
    Args:
        query (str): The SQL query to execute
        
    Returns:
        dict: A dictionary containing:
            - message (str): Summary of results found and limit applied
            - row_count (int): Number of rows returned
            - columns (list): List of column names
            - results (Union[list, str, dict]): Query results in specified format
            - format (str): Format of returned results
            - error (str): Error message if execution failed
    Raises:
        TimeoutError: If query execution exceeds max_execution_time from config
        Exception: For other database errors
    Notes:
        - Enforces execution timeout specified in config
        - Limits number of returned rows based on config
        - Supports multiple return formats: json, csv, list
        - Automatically uses default database path from config if not specified
    Example:
        result = execute_sql_query("SELECT * FROM users")
        print(result)   
    '''
    try:   
        # Get configuration
        tool_config = config.tool_execute_sql
        database_config = config.database_config
        max_time = tool_config.get('max_execution_time', 30)
        max_results = tool_config.get('max_results', 100)
        return_format = tool_config.get('return_format', 'json')
        db_path = database_config.get('default_path', 'database.db')  # Default database path
            
        # Set timeout
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(max_time)
            
        with sqlite3.connect(str(db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Get column names
            column_names = [description[0] for description in cursor.description] if cursor.description else []
            
            # Fetch limited results
            results = cursor.fetchall()
            limited_results = results[:max_results]
            
            # Reset alarm
            signal.alarm(0)
            
            # Format results according to return_format
            formatted_data = None
            if return_format.lower() == 'json':
                formatted_data = [dict(zip(column_names, row)) for row in limited_results]
            elif return_format.lower() == 'csv':
                output = StringIO()
                csv_writer = csv.writer(output)
                csv_writer.writerow(column_names)
                csv_writer.writerows(limited_results)
                formatted_data = output.getvalue()
            elif return_format.lower() == 'list':
                formatted_data = limited_results
            else:
                formatted_data = limited_results  # Default to list of tuples
            
            return {
                "message": f"{len(results)} results found (limited to {max_results})",
                "row_count": len(limited_results),
                "columns": column_names,
                "results": formatted_data,
                "format": return_format
            }
            
    except TimeoutError:
        return {"error": f"Query execution timed out after {max_time} seconds"}
    except Exception as e:
        return {"error": str(e)}
    finally:
        # Reset alarm in case of any errors
        signal.alarm(0)

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
        print(result)
if __name__ == "__main__":
    main()
