from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import json
from .pipeline import Pipeline
from utility.model import ConversationState, Message
from utility.StateManager import StateManager

app = FastAPI(title="Pipeline API")

# Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global conversation state
conversation_state = ConversationState()
state_manager = StateManager(initial_state=conversation_state)

# Request schemas
class StartRequest(BaseModel):
    user_query: str

class ContinueRequest(BaseModel):
    user_query: str

# POST /start (starts a new conversation)
@app.post("/start")
async def start_pipeline(request: StartRequest):
    global conversation_state, state_manager

    # Reset full state
    conversation_state = ConversationState()
    state_manager = StateManager(initial_state=conversation_state)
    state_manager.add_message(role="user", content=request.user_query)

    pipeline = Pipeline(request.user_query, state=state_manager.get_state())
    output = await pipeline.run()
    
    assistant_response = _extract_response_from_results(output)
    state_manager.add_message(role="assistant", content=assistant_response)

    return {
        "message": assistant_response,
        "stage": pipeline.stage.name,
        "results": output["results"] if output else None,
        "state": state_manager.get_state().model_dump()
    }

# POST /continue (adds a follow-up turn)
@app.post("/continue")
async def continue_pipeline(request: ContinueRequest):
    global conversation_state, state_manager

    state_manager.add_message(role="user", content=request.user_query)

    pipeline = Pipeline(request.user_query, state=state_manager.get_state())
    output = await pipeline.run()

    assistant_response = _extract_response_from_results(output)
    state_manager.add_message(role="assistant", content=assistant_response)

    return {
        "message": assistant_response,
        "stage": pipeline.stage.name,
        "results": output["results"] if output else None,  # <-- fixed key
        "state": state_manager.get_state().model_dump()
    }
# Helper function to extract assistant response from tool results
def _extract_response_from_results(output: dict) -> str:
    if output and "results" in output:
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
            messages.append(f"### Tool used: {tool_name}\n\n{explanation}")
        return "\n\n".join(messages)

    return "I'm sorry, I couldn't generate a response."

# GET /status
@app.get("/status")
async def get_status():
    state = state_manager.get_state()
    last_tool = state.last_tool_used

    results = {}
    if last_tool and last_tool in state.tool_memory:
        tool_data = state.tool_memory[last_tool].data
        if tool_data:
            results[last_tool] = {
                "output_text": state.messages[-2].content if len(state.messages) >= 2 else "No explanation available.",
                "raw_output": tool_data
            }

    return {
        "message": "Active pipeline status",
        "stage": "COMPLETED" if results else "IN_PROGRESS",  # You can improve this logic if needed
        "results": results if results else None,
        "state": state.model_dump()
    }
