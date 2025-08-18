import sys
from mcp.server.fastmcp import FastMCP
from .InsightGenerator import InsightGenerator
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from fastmcp import Client
from typing import List, Optional
from dotenv import load_dotenv
from utility.model import UserProfile, RetrievedDoc, InsightGeneratorInput, InsightGeneratorOutput

load_dotenv()

mcp = FastMCP("InsightGenerator", stateless_http=True)
RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-scheme/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def generate_insight(schema_dict: dict, documents: Optional[str] = None) -> dict:
    try:
        logger.info(f"[InsightGenerator] Received request: {schema_dict}")
        insight_generator = InsightGenerator()

        # Reshape the input dictionary into the required Pydantic model for the user profile
        user_profile_obj = UserProfile(**schema_dict.get("user_profile", {}))

        query_text = schema_dict.get("user_query", "")
        logger.info(f"Querying retriever with: '{query_text}'")
        
        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": query_text,
                    "caller_tool": mcp.name,
                    "top_k": 5
                }
            )

        docs_from_retriever = response.data.result
        if not isinstance(docs_from_retriever, list):
            logger.warning("Retrieved documents were not a list; resetting to []")
            docs_from_retriever = []
        
        # --- Applying the exact logic from your reference code ---
        logger.info(f"[InsightGenerator] Retrieved {len(docs_from_retriever)} documents.")

        doc_dicts = [vars(d) for d in docs_from_retriever]
        combined_content = "\n\n".join(doc.get("content", "") for doc in doc_dicts)
        logger.info(f"[InsightGenerator] Combined content length: {len(combined_content)}")
        # --- End of reference logic ---

        # Call the core logic with the reshaped data, matching the reference pattern
        result = insight_generator.generate_insight(
            user_query=query_text,
            user_profile=user_profile_obj.model_dump(), # Pass as dict, like in SchemeExplainer
            retrieved_documents=combined_content or None
        )
        
        return result

    except Exception as e:
        logger.error("Failed to generate insight", exc_info=True)
        raise UdayamitraException("Failed to generate insight", sys)


if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')