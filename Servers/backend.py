from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
import sys 
from .pipeline import Pipeline
from utility.model import ConversationState, Message
from utility.StateManager import StateManager
from Logging.logger import logger 
from Exception.exception import UdayamitraException 

import nest_asyncio
nest_asyncio.apply()

app = FastAPI(title="Pipeline API")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "https://udyamitra-frontend.vercel.app", "https://udyamitra-mcps.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ERROR_MESSAGE = "I'm sorry, I'm not able to help with that request. Please try a different query."

# Global conversation state
conversation_state = ConversationState()
state_manager = StateManager(initial_state=conversation_state)

# Request schemas
class StartRequest(BaseModel):
    user_query: str

class ContinueRequest(BaseModel):
    user_query: str

@app.get("/")
async def root():
    return {"message": "Pipeline API for backend is running."}

# POST /start (starts a new conversation)
# --- MODIFIED: Added try...except block ---
@app.post("/start")
async def start_pipeline(request: StartRequest):
    global conversation_state, state_manager

    # Reset full state
    conversation_state = ConversationState()
    state_manager = StateManager(initial_state=conversation_state)
    state_manager.add_message(role="user", content=request.user_query)

    try:
        pipeline = Pipeline(request.user_query, state=state_manager.get_state())
        output = await pipeline.run()
        
        # This handles the "no tools found" case where the pipeline
        # runs but doesn't produce any tool results (empty dictionary)
        if not output or "results" not in output or not output["results"]:
             logger.warning(f"Pipeline ran but returned no results (no tools found) for query: {request.user_query}")
             # We raise an exception to be caught by the 'except' block
             raise UdayamitraException("No tools were found or no plan could be executed for this query.", sys)

        assistant_response = _extract_response_from_results(output)
        stage = pipeline.stage.name
        results = output["results"]

    except Exception as e:
        # This catches any failure in the pipeline (crash, no tools, etc.)
        logger.error(f"Pipeline failed for query '{request.user_query}': {e}", exc_info=True)
        assistant_response = ERROR_MESSAGE
        stage = "FAILED"
        results = None
        # The server doesn't crash; it just returns this error message
    
    state_manager.add_message(role="assistant", content=assistant_response)

    return {
        "message": assistant_response,
        "stage": stage,
        "results": results,
        "state": state_manager.get_state().model_dump()
    }

# POST /continue (adds a follow-up turn)
# --- MODIFIED: Added try...except block ---
@app.post("/continue")
async def continue_pipeline(request: ContinueRequest):
    global conversation_state, state_manager

    state_manager.add_message(role="user", content=request.user_query)

    try:
        pipeline = Pipeline(request.user_query, state=state_manager.get_state())
        output = await pipeline.run()

        # This handles the "no tools found" case
        if not output or "results" not in output or not output["results"]:
             logger.warning(f"Pipeline ran but returned no results (no tools found) for query: {request.user_query}")
             raise UdayamitraException("No tools were found or no plan could be executed for this query.", sys)

        assistant_response = _extract_response_from_results(output)
        stage = pipeline.stage.name
        results = output["results"]

    except Exception as e:
        # This catches any failure in the pipeline
        logger.error(f"Pipeline failed for query '{request.user_query}': {e}", exc_info=True)
        assistant_response = ERROR_MESSAGE
        stage = "FAILED"
        results = None
    
    state_manager.add_message(role="assistant", content=assistant_response)

    return {
        "message": assistant_response,
        "stage": stage,
        "results": results,
        "state": state_manager.get_state().model_dump()
    }

# Helper function to extract assistant response from tool results
def _extract_response_from_results(output: dict) -> str:
    # This check is now redundant because of our new error handling,
    # but it's good to keep as a final fallback.
    if not output or "results" not in output or not output["results"]:
        return ERROR_MESSAGE

    results = output["results"]

    # Fix: decode if results is JSON string
    if isinstance(results, str):
        try:
            results = json.loads(results)
        except json.JSONDecodeError:
            return "Invalid results format."

    messages = []
    for tool_name, result in results.items():
        # result could be string or dict with output_text
        explanation = result.get("output_text") if isinstance(result, dict) else str(result)
        messages.append(f"{explanation}") # Removed the "Tool used:" part for a cleaner response
    
    return "\n\n".join(messages)

# GET /status
@app.get("/status")
async def get_status():
    state = state_manager.get_state()
    last_tool = state.last_tool_used

    results = {}
    if last_tool and last_tool in state.tool_memory:
        tool_data = state.tool_memory[last_tool].data
        if tool_data:
            # Try to get the *last assistant message* as the output_text
            last_assistant_message = ""
            for msg in reversed(state.messages):
                if msg.role == "assistant":
                    last_assistant_message = msg.content
                    break
            
            results[last_tool] = {
                "output_text": last_assistant_message,
                "raw_output": tool_data
            }

    stage = "IN_PROGRESS" # Default
    if state.messages:
        last_message = state.messages[-1]
        if last_message.role == "assistant":
            if last_message.content == ERROR_MESSAGE:
                stage = "FAILED" # The last query failed
            else:
                stage = "COMPLETED" # The last query succeeded
    # If the last message is 'user', stage remains 'IN_PROGRESS'

    return {
        "message": "Active pipeline status",
        "stage": stage, 
        "results": results if results else None,
        "state": state.model_dump()
    }