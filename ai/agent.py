import json
from typing import Any

from openai import OpenAI

import os

from ai.tool_registry import TOOLS, dispatch

MAX_TOOL_ROUNDS = 5
OPENAI_TIMEOUT = 30.0

SYSTEM_PROMPT = """You are a helpful assistant for a media server control panel.
You help the user manage their Radarr, Sonarr, SABnzbd, Jellyfin, Docker containers, and system.

You can use the available tools to:
- Search and add movies (Radarr) or TV series (Sonarr)
- Check download queue status and pause/resume downloads (SABnzbd)
- Browse recently added media (Jellyfin)
- Check and manage Docker containers
- Monitor system status and disk health

Rules:
- NEVER execute shell commands or system commands directly
- ONLY use the provided tools to interact with services
- Be concise and helpful in your responses
- If a tool call fails, explain the error clearly to the user
- When adding media, always confirm what was added with title and year
"""


def run_agent(messages: list[dict], settings: dict) -> str:
    """
    Run the multi-round OpenAI tool loop.

    Args:
        messages: Conversation history list of {role, content} dicts
        settings: The full settings dict from config.py

    Returns:
        The assistant's final response string
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    if not api_key:
        return "OpenAI API key is not configured. Please add it in Settings."

    client = OpenAI(api_key=api_key, timeout=OPENAI_TIMEOUT)

    # Build message list with system prompt
    all_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    for round_num in range(MAX_TOOL_ROUNDS):
        response = client.chat.completions.create(
            model=model,
            messages=all_messages,
            tools=TOOLS,
            tool_choice="auto"
        )

        choice = response.choices[0]
        message = choice.message

        # Add assistant message to history
        all_messages.append(message.model_dump(exclude_unset=False))

        # If no tool calls, we're done
        if choice.finish_reason == "stop" or not message.tool_calls:
            return message.content or ""

        # Process tool calls
        for tool_call in message.tool_calls:
            function_name = tool_call.function.name
            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            result = dispatch(function_name, arguments, settings)

            # Add tool result to messages
            all_messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result, ensure_ascii=False, default=str)
            })

    # If we exhausted rounds, get a final response
    response = client.chat.completions.create(
        model=model,
        messages=all_messages
    )
    return response.choices[0].message.content or "I was unable to complete the request."
