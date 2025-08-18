import sys
import json
import asyncio
import re
import ast
from datetime import datetime
from typing import Dict, Any, Union, Optional
from pydantic import BaseModel
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from router.ModelResolver import ModelResolver
from router.SchemaGenerator import SchemaGenerator
from utility.model import (
    ExecutionPlan,
    ToolTask,
    ToolRegistryEntry,
    Metadata,
)
from utility.StateManager import StateManager
from utility.register_tools import load_registry_from_file
from utility.LLM import LLMClient
from Logging.logger import logger
from Exception.exception import UdayamitraException

def safe_json_parse(raw_output: str) -> dict:
    import json, re

    raw_output = re.sub(r"```(?:json)?", "", raw_output.strip(), flags=re.IGNORECASE)

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        pass

    cleaned = raw_output.replace("'", '"')
    cleaned = re.sub(r",\s*([}\]])", r"\\1", cleaned)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.warning(f"[safe_json_parse] JSON still invalid: {e}")
        logger.warning("[safe_json_parse] Returning fallback raw_output string.")
        return {"output_text": raw_output}  # fallback

def ensure_dict(obj):
    return obj if isinstance(obj, dict) else {"output_text": str(obj)}

# -------------------- ADDED (generic passthrough helpers) --------------------
def _model_known_fields(schema_class) -> set:
    """
    Return the set of top-level field names of the Pydantic model.
    Supports Pydantic v1 (__fields__) and v2 (model_fields).
    """
    if hasattr(schema_class, "__fields__"):     # Pydantic v1
        return set(schema_class.__fields__.keys())
    if hasattr(schema_class, "model_fields"):   # Pydantic v2
        return set(schema_class.model_fields.keys())
    return set()

def _collect_extras_for_context(task_input: Dict[str, Any], known: set) -> Dict[str, Any]:
    """
    Any planner inputs not claimed by top-level schema fields are extras.
    We route them to context_entities.
    """
    return {k: v for k, v in (task_input or {}).items() if k not in known}
# ---------------------------------------------------------------------------

class ToolExecutor:
    def __init__(self, conversation_state: Optional[Any] = None):
        try:
            logger.info("Initializing ToolExecutor")
            self.tool_registry: Dict[str, ToolRegistryEntry] = load_registry_from_file()
            if not self.tool_registry:
                raise UdayamitraException("Tool registry is empty. Ensure tools are registered properly.", sys)

            self.resolver = ModelResolver("utility.model")
            self.schema_generator = SchemaGenerator()
            self.llm_client = LLMClient(model="meta-llama/llama-4-maverick-17b-128e-instruct")

            self.state_manager = StateManager(initial_state=conversation_state)
            self.conversation_state = self.state_manager.get_state()

            logger.info("ToolExecutor initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ToolExecutor: {e}")
            raise UdayamitraException("Failed to initialize ToolExecutor", sys)

    def _get_schema(self, tool_schema_name: str):
        try:
            logger.info(f"Resolving schema: {tool_schema_name}")
            model_class = self.resolver.resolve(tool_schema_name)
            logger.info(f"Resolved class: {model_class.__name__}")
            assert issubclass(model_class, BaseModel)
            return model_class
        except Exception as e:
            logger.error(f"Failed to resolve schema: {e}")
            raise UdayamitraException(f"Failed to resolve schema: {e}", sys)

    @asynccontextmanager
    async def connect_to_server_for_tool(self, tool_name: str):
        if tool_name not in self.tool_registry:
            raise UdayamitraException(f"Tool '{tool_name}' not found in registry.", sys)

        endpoint = self.tool_registry[tool_name].endpoint
        logger.info(f"Connecting to MCP server at {endpoint} for tool '{tool_name}'")

        async with streamablehttp_client(url=endpoint) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                logger.info("Initializing MCP session...")
                await session.initialize()
                logger.info(f"MCP session initialized for {endpoint}")
                yield session

    async def get_required_inputs(self, session: ClientSession, tool_name: str) -> dict:
        try:
            response = await session.list_tools()
            for tool in response.tools:
                return {"server_Tool": tool.name, "required_input": tool.inputSchema.get("required", [])}
            logger.warning(f"Tool '{tool_name}' not found in list_tools response.")
            return {"server_Tool": None, "required_input": []}
        except Exception as e:
            logger.error(f"Failed to fetch input schema for tool '{tool_name}': {e}")
            return {"server_Tool": None, "required_input": []}

    def _resolve_input(self, task: ToolTask, previous_outputs: Dict[str, Any]) -> Dict[str, Any]:
        if task.input_from:
            referenced = previous_outputs.get(task.input_from)
            if not referenced:
                raise UdayamitraException(
                    f"No output found from '{task.input_from}' to resolve input for '{task.tool_name}'", sys
                )
            if isinstance(referenced, dict):
                return {"output_text": referenced.get("output_text", str(referenced))}
            return {"output_text": str(referenced)}
        return task.input

    @staticmethod
    def format_explanation(raw: str) -> str:
        cleaned = raw.strip()
        if "\n" in cleaned:
            cleaned = cleaned.replace("\n", "\n")
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.replace("* ", "• ")
        if not cleaned.lower().startswith("here's a simple explanation"):
            cleaned = "Here's a simple explanation:\n\n" + cleaned
        return cleaned

    async def run_execution_plan(
        self,
        plan: ExecutionPlan,
        metadata: Metadata,
        flatten_output: bool = False
    ) -> Union[str, Dict[str, Any]]:
        results: Dict[str, Any] = {}

        # Sanitize metadata.entities
        if isinstance(metadata.entities.get("scheme"), list):
            metadata.entities["scheme"] = metadata.entities["scheme"][0]

        self.state_manager.add_message(role="user", content=metadata.query)

        if plan.execution_type != "sequential":
            raise UdayamitraException(f"Execution type '{plan.execution_type}' not supported yet.", sys)

        for task in plan.task_list:
            async with self.connect_to_server_for_tool(task.tool_name) as session:
                try:
                    required_inputs = await self.get_required_inputs(session, task.tool_name)
                    input_data = self._resolve_input(task, results)
                    schema_class = self._get_schema(self.tool_registry[task.tool_name].input_schema)

                    full_input = self.schema_generator.generate_instance(
                        metadata=metadata.model_dump(),
                        execution_plan=plan.model_dump(),
                        model_class=schema_class,
                        user_input=input_data,
                        state=self.conversation_state
                    )

                    # === Generic passthrough: route unknown planner keys -> context_entities ===
                    try:
                        known = _model_known_fields(schema_class)
                        extras = _collect_extras_for_context(task.input, known)

                        # Only merge if the target model actually has context_entities
                        if extras and ("context_entities" in known):
                            current_ctx = getattr(full_input, "context_entities", None) or {}
                            merged_ctx = {**current_ctx, **extras}

                            # Update the pydantic instance with merged context
                            full_input = full_input.copy(update={"context_entities": merged_ctx})

                            # Also expose to conversation state so downstream tools can reuse it
                            self.state_manager.update_context_entities(merged_ctx)
                    except Exception as _e:
                        logger.warning(f"[extras passthrough] skipped: {_e}")
                    # === End passthrough ===

                    logger.info(f"Calling tool '{task.tool_name}' with input: {full_input}")
                    wrapped_input = {"schema_dict": full_input.model_dump()}
                    logger.info(f"Wrapped input for tool '{task.tool_name}': {wrapped_input}")
                    response = await session.call_tool(required_inputs["server_Tool"], wrapped_input)

                    parsed = {}
                    if hasattr(response, "content") and response.content:
                        parsed = ensure_dict(safe_json_parse(response.content[0].text))

                    system_prompt = '''You are a helpful assistant that explains the output of a tool to the user, in an easy, detailed explainable way. 
Ensure you explain all the keys in the output. Dont summarize it, convert it to a simple explanation suitable for a user.
- Make sure you mention the sources at the end of the explanation.
- Do not provide any commentary (or preamble) before the explanation, just provide the explanation.
- You can add the follow up questions too, based on the context, make the subheading for it.
- If you have a JSON, do not explain what the keys mean, just focus on simplifying the "content" of the JSON.
'''
                    user_message = f"""Here is the tool's response:\n\n{json.dumps(parsed, indent=2)}\n\nPlease convert this into a simple explanation suitable for a user."""
                    final_explanation = self.llm_client.run_chat(system_prompt, user_message)

                    if isinstance(final_explanation, str) and '\\n' in final_explanation:
                        try:
                            final_explanation = ast.literal_eval(f"'''{final_explanation}'''")
                        except Exception:
                            final_explanation = final_explanation.replace("\\n", "\n")

                    formatted = self.format_explanation(raw=final_explanation)
                    results[task.tool_name] = {
                        "output_text": formatted,
                        "raw_output": parsed
                    }

                    self.state_manager.set_last_tool(task.tool_name)
                    self.state_manager.set_tool_memory(task.tool_name, parsed)
                    self.state_manager.add_message(role="tool", content=formatted, tool_used=task.tool_name)
                    self.state_manager.set_last_scheme(metadata.entities.get("scheme", ""))

                    merged_context = {
                        **metadata.entities,
                        **(metadata.user_profile.model_dump() if metadata.user_profile else {})
                    }
                    self.state_manager.update_context_entities(merged_context)

                except Exception as e:
                    logger.error(f"Error calling tool '{task.tool_name}': {e}")
                    results[task.tool_name] = f"Failed to process {task.tool_name}: {e}"

        if flatten_output and len(results) == 1:
            return next(iter(results.values()))

        logger.debug(f"[FINAL STATE BEFORE RETURN] {self.conversation_state.model_dump_json(indent=2)}")
        logger.info(f"Final Execution Results:\n{json.dumps(results, indent=2)}")
        return results if results else "No tools could be executed successfully."

    def get_state(self):
        return self.conversation_state
