import json
import re
import sys
from typing import List
from dotenv import load_dotenv

from utility.model import Metadata, ExecutionPlan, ToolTask, ConversationState
from utility.LLM import LLMClient
from router.ToolExecutor import safe_json_parse
from Logging.logger import logger
from Exception.exception import UdayamitraException

load_dotenv()

class Planner:
    def __init__(self, model: str = "meta-llama/llama-4-maverick-17b-128e-instruct"):
        try:
            logger.info(f"Initializing Planner with model: {model}")
            self.llm_client = LLMClient(model=model)
        except Exception as e:
            logger.error(f"Failed to initialize Planner: {e}")
            raise UdayamitraException("Failed to initialize Planner", sys)

    def build_plan(self, metadata: Metadata, state: ConversationState | None = None) -> ExecutionPlan:
        try:
            logger.info(f"Building execution plan for metadata: {metadata}")
            context_hint = ""

            if state:
                last_tool = state.last_tool_used or ""
                last_msg = state.messages[-1].content if state.messages else ""
                last_entities = state.context_entities or {}

                context_hint = f"""
## Conversation History (for context):
- Previous tool used: {last_tool}
- Last assistant message: {last_msg}
- Previously detected entities: {json.dumps(last_entities, indent=2)}
Use this context ONLY if the current query is an ambiguous follow-up.
""".strip()

            # UPDATED: A more restrictive system prompt.
            system_prompt = """
You are a precise and logical planning assistant. Your ONLY job is to create a JSON execution plan based on the user's query metadata.
You MUST follow these rules:
1.  You MUST ONLY use the tool names provided in the `tools_required` list from the input metadata.
2.  Do NOT invent, create, or hallucinate any tool names.
3.  If the `tools_required` list is empty, you MUST return a plan with an empty `tasks` list.
4.  Your entire response MUST be a single, valid JSON object and nothing else.
""".strip()

            # UPDATED: A clearer user prompt with explicit instructions.
            user_prompt = f"""
## INSTRUCTIONS
Create a JSON execution plan based on the provided metadata. Adhere strictly to the rules given by the system prompt.
The `input` for each tool should be constructed from the `query`, `entities`, and `user_profile` in the metadata.

## METADATA
{metadata.model_dump_json(indent=2)}

{context_hint}

## REQUIRED JSON OUTPUT FORMAT
{{
  "execution_type": "sequential",
  "tasks": [
    {{
      "tool": "ToolNameFromToolsRequiredList",
      "input": {{ ... }},
      "input_from": "OptionalPreviousTool"
    }}
  ]
}}
""".strip()

            raw_output = self.llm_client.run_chat(system_prompt, user_prompt)
            logger.info(f"Raw output from LLM:\n{raw_output}")

            plan_dict = safe_json_parse(raw_output)
            
            # Handle the case where the LLM correctly returns an empty task list
            tasks_data = plan_dict.get("tasks", [])
            if not tasks_data:
                logger.warning("Planner returned a plan with no tasks.")
                return ExecutionPlan(execution_type="sequential", task_list=[])

            logger.info(f"Parsed execution plan:\n{json.dumps(plan_dict, indent=2)}")

            task_list: List[ToolTask] = [
                ToolTask(
                    tool_name=task["tool"],
                    input=task["input"],
                    input_from=task.get("input_from")
                )
                for task in tasks_data
            ]

            return ExecutionPlan(
                execution_type=plan_dict["execution_type"],
                task_list=task_list
            )

        except Exception as e:
            logger.error(f"Failed to build execution plan: {e}")
            raise UdayamitraException(f"Planner failed: {e}", sys)