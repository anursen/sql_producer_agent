from services.agents.sql_assistant import SQLQueryAssistant
from tools.schema_analyzer import SchemaAnalyzer
import re
import json
from config import OPENAI_API_KEY

def validate_query(query: str) -> tuple[bool, str]:
    if not query.strip():
        return False, "Query cannot be empty"
    if len(query) > 1000:
        return False, "Query too long (max 1000 characters)"
    return True, ""

def debug_query(assistant: SQLQueryAssistant, query: str) -> dict:
    print("\nDEBUG MODE:")
    print("1. Analyzing query structure...")
    
    # Check for common SQL injection patterns
    if any(pattern in query.lower() for pattern in ["drop", "delete", "--", ";"]):
        print("⚠️ Warning: Potentially dangerous SQL operations detected")
        proceed = input("Do you want to proceed? (y/n): ").lower()
        if proceed != 'y':
            return {"error": "Query cancelled by user"}
    
    print("2. Generating SQL...")
    result = assistant.process_query(query)
    
    if "error" in result:
        print("\nERROR ANALYSIS:")
        if "no such table" in str(result["error"]):
            print("- Table might not exist in database")
            print("- Available tables: customers, orders, products, etc.")
        elif "syntax error" in str(result["error"]):
            print("- SQL syntax error detected")
            print("- Check query structure")
    
    return result

def main():
    # Validate API key first
    if not OPENAI_API_KEY or OPENAI_API_KEY.startswith('your-api-key'):
        print("Error: Please set a valid OpenAI API key in your .env file")
        return
        
    assistant = SQLQueryAssistant()
    analyzer = SchemaAnalyzer()
    debug_mode = False
    
    print("SQL Query Assistant")
    print("Commands:")
    print("- 'exit': Quit the program")
    print("- 'debug': Toggle debug mode")
    print("- 'schema': Show database schema")
    print("- 'analyze': Analyze database schema")
    print("- 'help': Show this help message")
    print("-" * 50)
    
    while True:
        try:
            query = input("\nEnter your question" + (" (DEBUG MODE)" if debug_mode else "") + ": ").strip()
            
            if query.lower() == 'exit':
                break
            elif query.lower() == 'debug':
                debug_mode = not debug_mode
                print(f"Debug mode {'enabled' if debug_mode else 'disabled'}")
                continue
            elif query.lower() == 'schema':
                schema = analyzer.get_schema_info(assistant.db_path)
                print("\nDatabase Schema:")
                print(json.dumps(schema, indent=2))
                continue
            elif query.lower() == 'analyze':
                schema_q = input("Enter schema analysis question (or press Enter for general analysis): ").strip()
                analysis = analyzer.analyze_schema(assistant.db_path, schema_q if schema_q else None)
                print("\nSchema Analysis:")
                print("-" * 50)
                print(analysis)
                continue
            elif query.lower() == 'help':
                continue
            
            # Validate query
            is_valid, error_msg = validate_query(query)
            if not is_valid:
                print(f"Error: {error_msg}")
                continue
            
            # Process query
            result = debug_query(assistant, query) if debug_mode else assistant.process_query(query)
            
            print("\nResults:")
            print("-" * 50)
            if "error" in result:
                print(f"Error: {result['error']}")
                if debug_mode:
                    suggestion = input("\nWould you like suggestions to fix this? (y/n): ").lower()
                    if suggestion == 'y':
                        print("\nSuggestions:")
                        print("1. Check table names and column references")
                        print("2. Verify SQL syntax")
                        print("3. Ensure proper data types are used")
            else:
                print(f"SQL Query: {result['sql']}")
                print("\nOutput:")
                if not result['results']:
                    print("No results found")
                else:
                    for row in result['results']:
                        print(row)
                
                if debug_mode:
                    print("\nQuery Stats:")
                    print(f"- Results returned: {len(result['results'])}")
                    
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            if debug_mode:
                import traceback
                print("\nFull traceback:")
                print(traceback.format_exc())

if __name__ == "__main__":
    main()
