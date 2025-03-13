import os
import uuid
from psycopg_pool import ConnectionPool
from langgraph.graph import StateGraph, MessagesState, START, END
langchain_postgres.checkpoint import PostgresSaver




# Initialize the PostgreSQL connection pool
pool = ConnectionPool(
    conninfo=f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@localhost:5432/{os.getenv('POSTGRES_DB')}",
    max_size=20,
    kwargs={"autocommit": True},
)

# Initialize the PostgresSaver with the connection pool
checkpointer = PostgresSaver(sync_connection=pool)

# Run setup to initialize the database schema (run once)
checkpointer.setup()

# Initialize the state graph
workflow = StateGraph(state_schema=MessagesState)

# Define a function to retrieve user memories
def retrieve_memories(state: MessagesState, store: PostgresSaver, user_id: str):
    namespace = ("memories", user_id)
    memories = store.search(namespace)
    return {"memories": [memory.value for memory in memories]}

# Define a function to process user input and update memory
def process_input(state: MessagesState, store: PostgresSaver, user_id: str):
    user_message = state["messages"][-1]["content"]
    # Process the message and generate a response (e.g., using an LLM)
    response = f"Processed message: {user_message}"
    # Update memory with the new information
    memory_key = str(uuid.uuid4())
    memory_value = {"content": user_message}
    store.put(("memories", user_id), memory_key, memory_value)
    return {"response": response}

# Add nodes to the workflow
workflow.add_node("retrieve_memories", retrieve_memories)
workflow.add_node("process_input", process_input)

# Define the workflow edges
workflow.add_edge(START, "retrieve_memories")
workflow.add_edge("retrieve_memories", "process_input")
workflow.add_edge("process_input", END)

# Compile the graph with the PostgresSaver
app = workflow.compile(checkpointer=checkpointer)

# Function to handle user sessions
def handle_user_session(user_id: str, user_input: str):
    thread_id = f"session_{user_id}"
    initial_state = {"messages": [{"content": user_input}]}
    config = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
    result = app.invoke(initial_state, config=config)
    return result["response"]

# Example usage
if __name__ == "__main__":
    user_id = "user123"
    user_input = "Hello, how can I update my profile?"
    response = handle_user_session(user_id, user_input)
    print(response)
