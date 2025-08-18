'''
InsightGenerator.py - This is the source code for the MCP server that will be specifically used to generate insights for investors.
'''

import sys
import json
from Logging.logger import logger
from Exception.exception import UdayamitraException
from utility.LLM import LLMClient
from sentence_transformers.cross_encoder import CrossEncoder
from typing import List, Dict

# Import the Pydantic models for input and output
from utility.model import InsightGeneratorInput, InsightGeneratorOutput, RetrievedDoc

class InsightGenerator:
    JSON_FORMAT_INSTRUCTIONS = """
    {
    "insight_summary": "A concise, one-sentence summary of the key insight based on the user's query.",
    "detailed_explanation": "A detailed but easy-to-understand explanation of the insight. Directly address the user's query and reference their profile. Explain the 'why' behind the insight.",
    "potential_benefits": [
        "List of potential benefits or upsides of acting on this insight.",
        "Each benefit should be a separate string in this list."
    ],
    "associated_risks": [
        "List of key risks or downsides the user must consider.",
        "Each risk should be a separate string in this list."
    ],
    "actionable_steps": [
        "A numbered list of concrete, practical steps the user can take next.",
        "Example: 1. Research Company X's Q4 earnings report.",
        "Example: 2. Consider diversifying with an ETF that tracks the S&P 500."
    ],
    "sources": [
        "List the specific document titles or identifiers used for this analysis.",
        "If no documents were used, return an empty list: []"
    ]
    }
    """

    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info("Starting InsightGenerator...")
            logger.info(f"Initializing InsightGenerator with model: {model}")
            self.llm_client = LLMClient(model=model)
            
            # Loads the reranker model into memory once at startup
            logger.info("Loading BAAI/bge-reranker-large model...")
            self.reranker_model = CrossEncoder('BAAI/bge-reranker-large')
            logger.info("All models loaded successfully.")
            
        except Exception as e:
            logger.error(f"Failed to initialize InsightGenerator: {e}")
            raise UdayamitraException("Failed to initialize InsightGenerator", sys)
            
    def _rerank_documents(self, query: str, documents: List[Dict]) -> List[Dict]:
        """A private function to rerank a small list of documents."""
        if not documents:
            return []
            
        # Assumes each dict in documents has a 'content' key
        doc_contents = [doc.get('content', '') for doc in documents]
        model_input_pairs = [[query, content] for content in doc_contents]
        
        scores = self.reranker_model.predict(model_input_pairs)
        
        for doc, score in zip(documents, scores):
            doc['rerank_score'] = float(score)
            
        return sorted(documents, key=lambda x: x['rerank_score'], reverse=True)

    def generate_insight(self, user_query: str, user_profile: dict, retrieved_documents: str = None) -> dict:
        try:
            system_prompt = """
            You are 'InsightBot', an expert financial analyst AI assistant. Your purpose is to provide clear, data-driven, and personalized investment insights to investors.

            You MUST adhere to the following principles:
            1.  **Data-First:** Your analysis MUST be based on the information provided in the "RETRIEVED DOCUMENTS". If the documents are insufficient, state that clearly in your explanation. Never invent facts.
            2.  **User-Centric:** Personalize the insight by considering the "USER PROFILE" (e.g., their risk tolerance, investment goals).
            3.  **Strict JSON Output:** Your entire response MUST be a single, valid JSON object. Do not include any text, explanations, or markdown formatting like ```json before or after the JSON object.
            """

            user_prompt = f"""
            Generate a personalized investment insight based on the user's request and the provided context. Follow the required JSON output format precisely.

            === USER QUERY ===
            {user_query}

            === USER PROFILE ===
            {json.dumps(user_profile, indent=2)}

            === RETRIEVED DOCUMENTS (Primary Source of Truth) ===
            {retrieved_documents if retrieved_documents else "No documents provided."}

            === REQUIRED JSON OUTPUT FORMAT ===
            {self.JSON_FORMAT_INSTRUCTIONS}
            """

            response_dict = self.llm_client.run_json(system_prompt, user_prompt)
            
            # Validate and return as a dictionary
            validated_output = InsightGeneratorOutput(**response_dict)
            return validated_output.model_dump()
        
        except Exception as e:
            logger.error(f"InsightGenerator failed: {e}")
            raise UdayamitraException("Failed to generate insights", sys)