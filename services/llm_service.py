from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

class LLMService:
    def __init__(self):
        self.llm = ChatOpenAI()
        
    async def process_message(self, message: str) -> str:
        # Basic implementation - expand based on your needs
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful SQL assistant."),
            ("user", "{input}")
        ])
        chain = prompt | self.llm
        response = await chain.ainvoke({"input": message})
        return response.content
