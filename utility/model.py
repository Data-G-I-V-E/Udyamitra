'''
model.py - This module defines the data model for the router configuration.
'''

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal, Union    

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