import sys
from mcp.server.fastmcp import FastMCP
from .EligibilityChecker import EligibilityChecker
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.register_tools import generate_tool_registry_entry, register_tool
from utility.model import EligibilityCheckRequest
from fastmcp import Client
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("EligibilityChecker", stateless_http=True)

RETRIEVER_URL = "http://127.0.0.1:10000/retrieve-scheme/mcp"
RETRIEVER_TOOL_NAME = "retrieve_documents"

@mcp.tool()
async def check_eligibility(schema_dict: dict) -> dict:
    try:
        logger.info(f"[EligibilityChecker] Received eligibility check request: {schema_dict}")
        checker = EligibilityChecker()
        request_obj = EligibilityCheckRequest(**schema_dict)

        query = request_obj.scheme_name.strip() or request_obj.model_dump_json()
        logger.debug(f"[EligibilityChecker] Querying retriever with: '{query}'")

        # Retrieve documents
        async with Client(RETRIEVER_URL) as retriever_client:
            response = await retriever_client.call_tool(
                RETRIEVER_TOOL_NAME,
                {"query": query, "caller_tool": mcp.name, "top_k": 5}
            )

        logger.debug(f"[EligibilityChecker] Retriever response: {response}")
        docs = response.data.result or []
        doc_dicts = [vars(d) for d in docs]
        combined_content = "\n\n".join(doc.get("content", "") for doc in doc_dicts)

        logger.info(f"[EligibilityChecker] Combined content length: {len(combined_content)}")

        # Run checker
        result = checker.check_eligibility(request=request_obj, retrieved_documents=combined_content or None)

        # Return structured dict directly
        return result

    except Exception as e:
        logger.error("Failed to check eligibility", exc_info=True)
        raise UdayamitraException("Failed to check eligibility", sys)
    
@mcp.tool()
async def interactive_check_eligibility(schema_dict: dict) -> dict:
    try:
        from .InteractiveEligibilityAgent import InteractiveEligibilityAgent

        logger.info(f"[InteractiveEligibilityAgent] Starting interactive loop")
        request_obj = EligibilityCheckRequest(**schema_dict)

        agent = InteractiveEligibilityAgent()
        final_response = agent.rerun(prev_request=request_obj, prev_response=agent.checker.check_eligibility(request_obj))

        return {
    "output_text": final_response["explanation"] if isinstance(final_response, dict) and "explanation" in final_response else str(final_response),
    "final_eligibility": final_response
}

    except Exception as e:
        logger.error("Failed interactive eligibility flow", exc_info=True)
        raise UdayamitraException("Interactive eligibility failed", sys)


if __name__ == "__main__":
    tool_info = generate_tool_registry_entry()
    register_tool(tool_info)
    mcp.run(transport='streamable-http')
