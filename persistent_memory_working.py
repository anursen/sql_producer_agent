from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, START, StateGraph
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import tools_condition, ToolNode

class MathTools:
    @staticmethod
    def add(a: int, b: int) -> int:
        """Add two numbers together.

        Args:
            a: The first number
            b: The second number

        Returns:
            The sum of the two numbers
        """
        return a + b

    @staticmethod
    def multiply(a: int, b: int) -> int:
        """Multiply two numbers together.

        Args:
            a: The first number
            b: The second number

        Returns:
            The product of the two numbers
        """
        return a * b

    @staticmethod
    def divide(a: int, b: int) -> float:
        """Divide first number by second number.

        Args:
            a: The dividend (number to be divided)
            b: The divisor (number to divide by)

        Returns:
            The result of dividing a by b
        """
        return a / b

class ChatAssistant:
    def __init__(self):
        # Setup tools and LLM
        self.tools = [MathTools.add, MathTools.multiply, MathTools.divide]
        self.llm = ChatOpenAI(model="gpt-4o")
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Create base graph
        self.graph = self._create_graph()
        
        # Store user sessions
        self.sessions = {}

    def _create_graph(self):
        builder = StateGraph(MessagesState)
        
        # Create assistant node
        def assistant(state: MessagesState):
            sys_msg = SystemMessage(content="You are a math assistant that can add, multiply, and divide.")
            return {"messages": [self.llm_with_tools.invoke([sys_msg] + state["messages"])]}
        
        # Build graph
        builder.add_node("assistant", assistant)
        builder.add_node("tools", ToolNode(self.tools))
        builder.add_edge(START, "assistant")
        builder.add_conditional_edges("assistant", tools_condition)
        builder.add_edge("tools", "assistant")
        
        return builder

    def get_user_session(self, user_id: str):
        """Get or create user session"""
        if user_id not in self.sessions:
            memory = MemorySaver()
            self.sessions[user_id] = {
                'memory': memory,
                'graph': self.graph.compile(checkpointer=memory)
            }
        return self.sessions[user_id]

    def process_query(self, user_id: str, query: str):
        """Process a user query"""
        session = self.get_user_session(user_id)
        config = {"configurable": {"thread_id": user_id}}
        
        # Process query
        messages = [HumanMessage(content=query)]
        result = session['graph'].invoke({"messages": messages}, config)
        
        return result, session['memory'], config

def main():
    assistant = ChatAssistant()
    print("Math Assistant (type 'exit' to quit)")
    print("-----------------------------------")

    while True:
        user_id = input("\nUser ID: ").strip()
        if user_id.lower() == 'exit':
            break

        query = input("Question: ").strip()
        if query.lower() == 'exit':
            break

        # Process query
        result, memory, config = assistant.process_query(user_id, query)

        # Show response
        print("\nResponse:")
        for msg in result['messages']:
            msg.pretty_print()

        # Show memory state
        checkpoint = memory.get(config)
        if checkpoint:
            print("\nMemory: Active")
        else:
            print("\nMemory: Empty")

if __name__ == "__main__":
    main()

"""
CHAT MEMORY ARCHITECTURE NOTES
============================

1. Memory Management
------------------
- Each user session has its own MemorySaver instance
- Memory is stored in self.sessions[user_id]['memory']
- Current structure:
    {
        'user_id_1': {
            'memory': MemorySaver instance,
            'graph': Compiled graph instance
        }
    }

2. Checkpoint Data Structure
-------------------------
- Checkpoints are stored per conversation using thread_id
- Access via: memory.get(config)
- Config format: {"configurable": {"thread_id": user_id}}
- Checkpoint contains:
    - Message history
    - Tool executions
    - State transitions

3. For MongoDB Integration
------------------------
Required fields to store:
    - user_id: str (unique identifier)
    - thread_id: str (from config)
    - timestamp: datetime
    - checkpoint_data: dict (from memory.get(config))
    - messages: list (conversation history)

Example MongoDB Schema:
{
    "user_id": "user_123",
    "thread_id": "user_123",
    "timestamp": ISODate("2024-01-01T00:00:00Z"),
    "checkpoint_data": {
        // Raw checkpoint data from MemorySaver
    },
    "messages": [
        // Array of message objects
    ]
}

4. Upcoming MongoDB Integration
----------------------------
TODO: Create methods for:
1. save_memory_to_mongo(user_id, checkpoint_data)
2. load_memory_from_mongo(user_id)
3. list_user_sessions()
4. delete_user_session(user_id)

Note: The MemorySaver checkpoint data can be serialized to JSON
for MongoDB storage and restored when needed.
"""


