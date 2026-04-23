"""
ai_provider.py — AI provider abstraction layer.

Supports: Claude (Anthropic), Gemini (Google), ChatGPT (OpenAI), Grok (xAI).
Each provider implements the same interface: send messages with tools, get back
text responses and tool calls, handle the tool-use loop.

Set AI_PROVIDER in .env to switch providers. Only the active provider's SDK
needs to be installed.
"""

import json
from abc import ABC, abstractmethod

from . import config


class AIProvider(ABC):
    """Base class for AI providers. All providers implement the same interface."""

    @abstractmethod
    def chat_with_tools(
        self,
        system_prompt: str,
        user_message: str,
        tool_schemas: list[dict],
        execute_tool_fn,
        log_fn,
        max_iterations: int = 10,
    ) -> None:
        """
        Run a full conversation with tool use.

        Args:
            system_prompt: System-level instructions for the AI
            user_message: The user's message to start the conversation
            tool_schemas: List of tool definitions (in Claude/OpenAI format)
            execute_tool_fn: Callable(name, input) -> (result_json, is_error)
            log_fn: Callable(message) for logging
            max_iterations: Max number of AI round-trips
        """
        pass


# =============================================================================
# Claude (Anthropic)
# =============================================================================

class ClaudeProvider(AIProvider):
    """Anthropic Claude with native tool use."""

    def __init__(self):
        import anthropic
        self.client = anthropic.Anthropic(api_key=config.AI_API_KEY)
        self.model = config.AI_MODEL

    def chat_with_tools(self, system_prompt, user_message, tool_schemas, execute_tool_fn, log_fn, max_iterations=10):
        messages = [{"role": "user", "content": user_message}]

        for iteration in range(max_iterations):
            log_fn(f"--- AI call #{iteration + 1} ({self.model}) ---")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=tool_schemas,
                messages=messages,
            )

            log_fn(f"Stop reason: {response.stop_reason}")

            assistant_content = response.content
            tool_results = []

            for block in assistant_content:
                if block.type == "text":
                    log_fn(f"AI: {block.text}")
                elif block.type == "tool_use":
                    tool_results.append(
                        self._handle_tool_call(block.name, block.input, block.id, execute_tool_fn, log_fn)
                    )

            if response.stop_reason == "end_turn":
                log_fn("AI finished (end_turn)")
                break

            if tool_results:
                messages.append({"role": "assistant", "content": assistant_content})
                messages.append({"role": "user", "content": tool_results})
            else:
                log_fn(f"Unexpected stop_reason: {response.stop_reason}, breaking")
                break
        else:
            log_fn(f"WARNING: Hit max iterations ({max_iterations})")

    def _handle_tool_call(self, name, tool_input, tool_id, execute_tool_fn, log_fn):
        log_fn(f"TOOL CALL: {name}({json.dumps(tool_input, default=str)})")
        result_str, is_error = execute_tool_fn(name, tool_input)
        self._log_tool_result(log_fn, name, result_str)
        tool_result = {"type": "tool_result", "tool_use_id": tool_id, "content": result_str}
        if is_error:
            tool_result["is_error"] = True
        return tool_result

    @staticmethod
    def _log_tool_result(log_fn, name, result_str):
        if len(result_str) > 500:
            log_fn(f"TOOL RESULT ({name}): {result_str[:500]}... [truncated]")
        else:
            log_fn(f"TOOL RESULT ({name}): {result_str}")


# =============================================================================
# ChatGPT (OpenAI) — also used as base for Grok
# =============================================================================

class OpenAIProvider(AIProvider):
    """OpenAI ChatGPT with function calling."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        import openai
        kwargs = {"api_key": api_key or config.AI_API_KEY}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = openai.OpenAI(**kwargs)
        self.model = config.AI_MODEL

    def _convert_tool_schemas(self, claude_schemas: list[dict]) -> list[dict]:
        """Convert Claude-format tool schemas to OpenAI function-calling format."""
        openai_tools = []
        for schema in claude_schemas:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": schema["name"],
                    "description": schema["description"],
                    "parameters": schema["input_schema"],
                },
            })
        return openai_tools

    def chat_with_tools(self, system_prompt, user_message, tool_schemas, execute_tool_fn, log_fn, max_iterations=10):
        openai_tools = self._convert_tool_schemas(tool_schemas)
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for iteration in range(max_iterations):
            log_fn(f"--- AI call #{iteration + 1} ({self.model}) ---")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=openai_tools,
                max_tokens=4096,
            )

            choice = response.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason

            log_fn(f"Finish reason: {finish_reason}")

            # Log any text content
            if message.content:
                log_fn(f"AI: {message.content}")

            # Handle tool calls
            if message.tool_calls:
                messages.append(message)  # Add assistant message with tool calls

                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    try:
                        tool_input = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        tool_input = {}

                    log_fn(f"TOOL CALL: {name}({json.dumps(tool_input, default=str)})")
                    result_str, is_error = execute_tool_fn(name, tool_input)
                    self._log_tool_result(log_fn, name, result_str)

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_str,
                    })
            elif finish_reason == "stop":
                log_fn("AI finished (stop)")
                break
            else:
                log_fn(f"Unexpected finish_reason: {finish_reason}, breaking")
                break
        else:
            log_fn(f"WARNING: Hit max iterations ({max_iterations})")

    @staticmethod
    def _log_tool_result(log_fn, name, result_str):
        if len(result_str) > 500:
            log_fn(f"TOOL RESULT ({name}): {result_str[:500]}... [truncated]")
        else:
            log_fn(f"TOOL RESULT ({name}): {result_str}")


# =============================================================================
# Grok (xAI) — OpenAI-compatible API at api.x.ai
# =============================================================================

class GrokProvider(OpenAIProvider):
    """xAI Grok — uses OpenAI-compatible API."""

    def __init__(self):
        super().__init__(
            base_url="https://api.x.ai/v1",
            api_key=config.AI_API_KEY,
        )


# =============================================================================
# Gemini (Google)
# =============================================================================

class GeminiProvider(AIProvider):
    """Google Gemini with function calling."""

    def __init__(self):
        import google.generativeai as genai
        genai.configure(api_key=config.AI_API_KEY)
        self.genai = genai
        self.model_name = config.AI_MODEL

    def _convert_tool_schemas(self, claude_schemas: list[dict]) -> list:
        """Convert Claude-format tool schemas to Gemini FunctionDeclaration format."""
        declarations = []
        for schema in claude_schemas:
            # Gemini uses 'parameters' directly (same JSON Schema format)
            declarations.append(self.genai.protos.FunctionDeclaration(
                name=schema["name"],
                description=schema["description"],
                parameters=schema["input_schema"],
            ))
        return declarations

    def chat_with_tools(self, system_prompt, user_message, tool_schemas, execute_tool_fn, log_fn, max_iterations=10):
        declarations = self._convert_tool_schemas(tool_schemas)
        tool_config = self.genai.protos.Tool(function_declarations=declarations)

        model = self.genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=system_prompt,
            tools=[tool_config],
        )

        chat = model.start_chat()
        current_message = user_message

        for iteration in range(max_iterations):
            log_fn(f"--- AI call #{iteration + 1} ({self.model_name}) ---")

            response = chat.send_message(current_message)

            has_tool_calls = False

            for part in response.parts:
                # Text response
                if part.text:
                    log_fn(f"AI: {part.text}")

                # Function call
                if hasattr(part, "function_call") and part.function_call.name:
                    has_tool_calls = True
                    name = part.function_call.name
                    # Convert MapComposite args to regular dict
                    tool_input = dict(part.function_call.args) if part.function_call.args else {}

                    log_fn(f"TOOL CALL: {name}({json.dumps(tool_input, default=str)})")
                    result_str, is_error = execute_tool_fn(name, tool_input)
                    self._log_tool_result(log_fn, name, result_str)

                    # Send function response back to Gemini
                    try:
                        result_data = json.loads(result_str)
                    except json.JSONDecodeError:
                        result_data = {"result": result_str}

                    current_message = self.genai.protos.Content(
                        parts=[self.genai.protos.Part(
                            function_response=self.genai.protos.FunctionResponse(
                                name=name,
                                response=result_data,
                            )
                        )]
                    )

            if not has_tool_calls:
                log_fn("AI finished (no more tool calls)")
                break
        else:
            log_fn(f"WARNING: Hit max iterations ({max_iterations})")

    @staticmethod
    def _log_tool_result(log_fn, name, result_str):
        if len(result_str) > 500:
            log_fn(f"TOOL RESULT ({name}): {result_str[:500]}... [truncated]")
        else:
            log_fn(f"TOOL RESULT ({name}): {result_str}")


# =============================================================================
# Factory
# =============================================================================

PROVIDERS = {
    "claude": ClaudeProvider,
    "chatgpt": OpenAIProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "grok": GrokProvider,
}

# Default models per provider (used if AI_MODEL is not set in .env)
DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-20250514",
    "chatgpt": "gpt-4.1",
    "openai": "gpt-4.1",
    "gemini": "gemini-2.5-flash",
    "grok": "grok-3",
}


def get_provider() -> AIProvider:
    """Create and return the configured AI provider."""
    name = config.AI_PROVIDER.lower()
    if name not in PROVIDERS:
        raise ValueError(
            f"Unknown AI_PROVIDER: '{name}'. "
            f"Supported: {', '.join(PROVIDERS.keys())}"
        )

    # Set default model if not explicitly configured
    if not config.AI_MODEL:
        config.AI_MODEL = DEFAULT_MODELS[name]

    return PROVIDERS[name]()
