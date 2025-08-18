import sys
from mcp.server.fastmcp import FastMCP
from .SchemeExplainer import SchemeExplainer
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import SchemeMetadata
from fastmcp import Client
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("SchemeExplainer", stateless_http=True)

RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-scheme/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def explain_scheme(schema_dict: dict, documents: Optional[str] = None) -> dict:
    try:
        logger.info(f"Received request to explain scheme: {schema_dict}")
        scheme_explainer = SchemeExplainer()

        reshaped_metadata = {
            "scheme_name": schema_dict.get("entities", {}).get("scheme_name", ""),
            "user_profile": schema_dict.get("user_profile", {}),
            "context_entities": schema_dict.get("entities", {}),
            "detected_intents": schema_dict.get("intents", []),
            "query": schema_dict.get("query", ""),
        }
        metadata_obj = SchemeMetadata(**reshaped_metadata)

        query = reshaped_metadata["scheme_name"].strip() or metadata_obj.model_dump()
        logger.info(f"[Explainer] Querying retriever with: '{query}', with type: {type(query)}")
        logger.debug(f"[Explainer] Calling retriever with query: '{query}' | Collection: 'chunks'")

        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {
                    "query": query["query"],
                    "caller_tool": mcp.name,  
                    "top_k": 5
                }
            )

        logger.debug(f"[Explainer] Raw retriever response: {response}")
        logger.warning(f"[Explainer] response.data → {response.data} (type={type(response.data)})")

        docs = response.data.result
        if not isinstance(docs, list):
            logger.warning("[Explainer] Retrieved documents were not a list; resetting to []")
            docs = []
        
        for d in docs:
            logger.debug(f"[Explainer] Raw doc object: {d} | type={type(d)} | keys={vars(d).keys()}")

        logger.info(f"[Explainer] Retrieved {len(docs)} documents from 'Scheme_chunks'.")

        doc_dicts = [vars(d) for d in docs]
        combined_content = "\n\n".join(doc.get("content", "") for doc in doc_dicts)
        logger.info(f"[Explainer] Combined content length: {len(combined_content)}")

        result = scheme_explainer.explain_scheme(
            scheme_metadata=metadata_obj,
            retrieved_documents=combined_content or None
        )
        return result

    except Exception as e:
        logger.error("Failed to explain scheme", exc_info=True)
        raise UdayamitraException("Failed to explain scheme", sys)


if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')
