import sqlite3
from typing import Dict, List

class SchemaAnalyzer:
    def get_schema_info(self, db_path: str) -> Dict[str, List[Dict]]:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        schema_info = {
            "tables": [],
            "relationships": [],
            "indexes": []
        }
        
        # Get tables and their columns
        tables = cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
        """).fetchall()
        
        for table in tables:
            table_name = table[0]
            columns = cursor.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            foreign_keys = cursor.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
            indexes = cursor.execute(f"PRAGMA index_list('{table_name}')").fetchall()
            
            table_info = {
                "name": table_name,
                "columns": [
                    {
                        "name": col[1],
                        "type": col[2],
                        "notnull": bool(col[3]),
                        "pk": bool(col[5])
                    } for col in columns
                ],
                "foreign_keys": [
                    {
                        "from": fk[3],
                        "to_table": fk[2],
                        "to_column": fk[4]
                    } for fk in foreign_keys
                ]
            }
            schema_info["tables"].append(table_info)
            
            for idx in indexes:
                schema_info["indexes"].append({
                    "table": table_name,
                    "name": idx[1],
                    "unique": bool(idx[2])
                })
        
        conn.close()
        return schema_info

    def get_readable_schema(self, db_path: str) -> str:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        tables = cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """).fetchall()
        
        output = []
        counter = 1
        
        for table in tables:
            table_name = table[0]
            # Get columns
            columns = cursor.execute(f"PRAGMA table_info('{table_name}')").fetchall()
            # Get foreign keys
            foreign_keys = cursor.execute(f"PRAGMA foreign_key_list('{table_name}')").fetchall()
            
            # Start table section
            output.append(f"{counter}. {table_name}")
            
            # Process columns
            for col in columns:
                name = col[1]
                data_type = col[2]
                is_pk = bool(col[5])
                
                # Find if column is a foreign key
                fk_info = next((fk for fk in foreign_keys if fk[3] == name), None)
                
                # Build column description
                desc = f"   - {name} ({data_type}"
                if is_pk:
                    desc += ", primary key"
                if fk_info:
                    desc += f", foreign key referencing {fk_info[2]}.{fk_info[4]}"
                desc += ")"
                
                output.append(desc)
            
            output.append("")  # Empty line between tables
            counter += 1
        
        conn.close()
        return "\n".join(output)

def print_menu():
    print("\nSchema Analyzer Menu:")
    print("1. Get Raw Schema Info (JSON format)")
    print("2. Get Readable Schema")
    print("3. Run Test Cases")
    print("4. Exit")

def run_test_cases(analyzer):
    print("\nRunning Test Cases:")
    print("-----------------")
    
    test_cases = [
        {
            "name": "Test Case 1: Chinook Database Schema",
            "db_path": "chinook.db",
            "function": "both"
        },
        {
            "name": "Test Case 2: Empty Database",
            "db_path": "test_empty.db",
            "function": "readable"
        },
         {
            "name": "Test Case 3: SQl Store",
            "db_path": "sql_store.db",
            "function": "readable"
        },
        # Add more test cases as needed
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        try:
            if test['function'] in ['raw', 'both']:
                print("\nRaw Schema Info:")
                schema_info = analyzer.get_schema_info(test['db_path'])
                print(json.dumps(schema_info, indent=2))
            
            if test['function'] in ['readable', 'both']:
                print("\nReadable Schema:")
                readable_schema = analyzer.get_readable_schema(test['db_path'])
                print(readable_schema)
                
        except Exception as e:
            print(f"Error in test case: {str(e)}")

if __name__ == "__main__":
    import json
    analyzer = SchemaAnalyzer()
    db_path = "chinook.db"  # default database
    
    while True:
        print_menu()
        choice = input("\nEnter your choice (1-4): ")
        
        try:
            if choice == '1':
                schema_info = analyzer.get_schema_info(db_path)
                print("\nSchema Info (JSON format):")
                print(json.dumps(schema_info, indent=2))
                
            elif choice == '2':
                schema = analyzer.get_readable_schema(db_path)
                print("\nReadable Schema:")
                print("---------------")
                print(schema)
                
            elif choice == '3':
                run_test_cases(analyzer)
                
            elif choice == '4':
                print("Exiting...")
                break
                
            else:
                print("Invalid choice. Please try again.")
                
            input("\nPress Enter to continue...")
            
        except Exception as e:
            print(f"Error: {str(e)}")
            input("\nPress Enter to continue...")
