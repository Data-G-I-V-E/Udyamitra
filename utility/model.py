'''
model.py - This module defines the data model for the router configuration.
'''

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal, Union    
from datetime import datetime

class Location(BaseModel):
    raw: str
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]

class UserProfile(BaseModel):
    user_type: str  # e.g., "woman-entrepreneur", "student"
    location: Location

class Metadata(BaseModel):
    query: str
    intents: List[str]
    tools_required: List[str]
    entities: Dict[str, Union[str, List[str]]]
    user_profile: Optional[UserProfile]

class ToolRegistryEntry(BaseModel):
    tool_name: str
    intents: List[str]
    endpoint: str
    input_schema: str
    output_schema: str
    model: Optional[str] = None
    description: Optional[str] = None

class ToolTask(BaseModel):
    tool_name: str
    input: Dict[str, Any]
    input_from: Optional[str] = None # incase there is dependency on another tool's output

class ExecutionPlan(BaseModel):
    execution_type:  Literal["sequential", "parallel"]
    task_list: List[ToolTask]

# --- Scheme Explainer ---
class SchemeMetadata(BaseModel):
    scheme_name: str
    user_profile: UserProfile
    context_entities: Optional[Dict[str, Union[str, List[str]]]] = None
    detected_intents: Optional[List[str]] = None
    query: Optional[str] = None

class SchemeExplanationResponse(BaseModel):
    scheme_name: str
    explanation: str
    follow_up_suggestions: Optional[List[str]] = Field(default_factory=list)
    sources: Optional[List[str]] = None

class EligibilityCheckRequest(BaseModel):
    scheme_name: str
    user_profile: UserProfile
    context_entities: Optional[Dict[str, Union[str, List[str]]]] = None  # e.g. {"age": "28", "category": "SC", "sector": "manufacturing"}
    query: Optional[str] = None  # original query from user, for logging/debugging

class EligibilityCheckResponse(BaseModel):
    scheme_name: str
    eligible: Optional[bool]  # True / False / None (if not enough data)
    reasons: List[str]
    missing_fields: Optional[List[str]] = None  # What else we need to decide
    sources: Optional[List[str]] = None  # Where the rule came from

# Scheme Retriever
class RetrievedDoc(BaseModel):
    content: str
    metadata: Optional[dict] = {}

class RetrieverOutput(BaseModel):
    result: List[RetrievedDoc]

# State Manager
class Message(BaseModel):
    role: Literal['user', 'assistant', 'system', 'tool']
    content: str
    tool_used: Optional[str] = None
    timestamp: Optional[datetime] = None

class ToolMemory(BaseModel):
    tool_name: str
    data: Dict[str, Any] = {}

class ConversationState(BaseModel):
    messages: List[Message] = []
    
    # Core memory
    user_profile: Optional[UserProfile] = None
    context_entities: Dict[str, Any] = {}

    # Tool-related memory
    last_tool_used: Optional[str] = None
    last_intent: Optional[str] = None
    last_scheme_mentioned: Optional[str] = None 
    tool_memory: Dict[str, ToolMemory] = {}

    # Dynamic state
    missing_inputs: Dict[str, List[str]] = {}  # tool_name -> list of missing fields

class InsightGeneratorInput(BaseModel):
    user_query: str = Field(..., description="The original, verbatim query from the user.")
    user_profile: UserProfile = Field(..., description="The user's profile, including location and type.")
    retrieved_documents: List[RetrievedDoc] = Field(..., description="The list of documents retrieved from the vector database, ranked by similarity.")

class InsightGeneratorOutput(BaseModel):
    insight_summary: str = Field(..., description="A concise, one-sentence summary of the key insight.")
    # detailed_explanation: str = Field(..., description="A detailed but easy-to-understand explanation of the insight.")
    # potential_benefits: List[str] = Field(..., description="A list of potential benefits or upsides of acting on this insight.")
    # associated_risks: List[str] = Field(..., description="A list of key risks or downsides the user must consider.")
    # actionable_steps: List[str] = Field(..., description="A list of concrete, practical steps the user can take next.")
    # sources: List[str] = Field(..., description="List of the specific document titles or identifiers used for the analysis.")

class InsightGeneratorInput(BaseModel):
    user_query: str = Field(..., description="The original, verbatim query from the user.")
    user_profile: UserProfile = Field(..., description="The user's profile, including location and type.")
    retrieved_documents: List[RetrievedDoc] = Field(..., description="The list of documents retrieved from the vector database, ranked by similarity.")

class InsightGeneratorOutput(BaseModel):
    insight_summary: str = Field(..., description="A concise, one-sentence summary of the key insight.")
    detailed_explanation: str = Field(..., description="A detailed but easy-to-understand explanation of the insight.")
    potential_benefits: List[str] = Field(..., description="A list of potential benefits or upsides of acting on this insight.")
    associated_risks: List[str] = Field(..., description="A list of key risks or downsides the user must consider.")
    actionable_steps: List[str] = Field(..., description="A list of concrete, practical steps the user can take next.")
    sources: List[str] = Field(..., description="List of the specific document titles or identifiers used for the analysis.")