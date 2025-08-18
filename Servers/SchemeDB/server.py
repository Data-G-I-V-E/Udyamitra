import os
import sys
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from Logging.logger import logger
from Exception.exception import UdayamitraException
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_astradb import AstraDBVectorStore
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import RetrievedDoc, RetrieverOutput

load_dotenv()
ASTRA_DB_ENDPOINT = os.getenv("ASTRA_DB_ENDPOINT")
ASTRA_DB_TOKEN    = os.getenv("ASTRA_DB_TOKEN")
if not ASTRA_DB_ENDPOINT or not ASTRA_DB_TOKEN:
    raise RuntimeError("ASTRA_DB_ENDPOINT and ASTRA_DB_TOKEN must be set")

logger.info("Initializing embeddings and vector stores for Retriever…")
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

vector_stores = {
    "Investor_policies": AstraDBVectorStore(
        embedding=embeddings,
        collection_name="Investor_policies", # Collection for InsightGenerator
        namespace=os.getenv("ASTRA_DB_KEYSPACE"),
        api_endpoint=ASTRA_DB_ENDPOINT,
        token=ASTRA_DB_TOKEN,
    ),
    "Scheme_chunks": AstraDBVectorStore(
        embedding=embeddings,
        collection_name="scheme_chunks", # Collection for SchemeExplainer
        namespace=os.getenv("ASTRA_DB_KEYSPACE"),
        api_endpoint=ASTRA_DB_ENDPOINT,
        token=ASTRA_DB_TOKEN,
    ),
    "Schemes_metadata": AstraDBVectorStore(
        embedding=embeddings,
        collection_name="Schemes_metadata", # Kept for other potential uses
        namespace=os.getenv("ASTRA_DB_KEYSPACE"),
        api_endpoint=ASTRA_DB_ENDPOINT,
        token=ASTRA_DB_TOKEN,
    )
}
logger.info("Retriever vector stores ready.")

COLLECTION_MAP = {
    "InsightGenerator": "Investor_policies",
    "SchemeExplainer": "Scheme_chunks"
}

mcp = FastMCP("SchemeDB", stateless_http=True)

@mcp.tool()
async def retrieve_documents(query: str, caller_tool: str, top_k: int = 5) -> RetrieverOutput:
    logger.info(f"[Retriever] Query received from '{caller_tool}' → query: '{query}' | top_k: {top_k}")
    
    collection_name = COLLECTION_MAP.get(caller_tool)
    if not collection_name:
        raise UdayamitraException(f"Invalid caller_tool: '{caller_tool}'. No collection mapping found.", sys)

    store = vector_stores.get(collection_name)
    if not store:
        raise UdayamitraException(f"Server error: No vector store configured for collection '{collection_name}'", sys)

    try:
        docs = store.similarity_search(query=query, k=top_k)
        logger.info(f"[Retriever] Found {len(docs)} matching docs from '{collection_name}'.")
        for i, doc in enumerate(docs):
            logger.debug(f"[Retriever] Doc {i+1}: {doc.page_content[:120]!r} | Metadata: {doc.metadata}")
            
        return RetrieverOutput(result=[
            RetrievedDoc(content=d.page_content, metadata=d.metadata) for d in docs
        ])
    except Exception as e:
        logger.error(f"[Retriever] Error fetching docs: {e}", exc_info=True)
        raise UdayamitraException("Failed to retrieve documents", sys)

if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport="streamable-http")