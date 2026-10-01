import logging

import anthropic
from pydantic import ValidationError

from src.agent.nodes.prompts import voice_director_prompt
from src.agent.state import SatsangState
from src.audio.tts.script import VoiceScript, plain_script, sanitize_tags, spoken_words
from src.config import DIRECTOR_MAX_TOKENS, DIRECTOR_TIMEOUT_SECONDS, HAIKU_MODEL

logger = logging.getLogger(__name__)

# The tool is forced so Haiku returns exactly a VoiceScript, with nothing to parse
TOOL = {
    "name": "write_script",
    "description": "Record the script the speech model will read aloud.",
    "input_schema": VoiceScript.model_json_schema(),
}


def _director_input(state: SatsangState) -> str:
    return f"The guide's answer (mode: {state['mode']}):\n\n{state['messages'][-1].content}"


def make_voice_director_node(client: anthropic.Anthropic):
    """
    Factory that captures the Anthropic client, built once at startup, in a closure.

    The director may place pauses but never change a word. If the words differ, or the call
    fails, the answer is spoken as it stands: the wording of a crisis reply, or of a passage,
    must reach the listener exactly as written.
    """
    def voice_director_node(state: SatsangState) -> dict:
        answer = state["messages"][-1].content
        try:
            response = client.messages.create(
                model=HAIKU_MODEL,
                max_tokens=DIRECTOR_MAX_TOKENS,
                timeout=DIRECTOR_TIMEOUT_SECONDS,
                system=voice_director_prompt(state["intent"]),
                tools=[TOOL],
                tool_choice={"type": "tool", "name": TOOL["name"]},
                messages=[{"role": "user", "content": _director_input(state)}],
            )
            tool_use = next(b for b in response.content if b.type == "tool_use")
            script = VoiceScript.model_validate(tool_use.input)
        except (anthropic.AnthropicError, StopIteration, ValidationError) as error:
            # Only the class is logged: the error text can carry the answer
            logger.warning("Voice director failed: %s", type(error).__name__)
            return {"voice_script": plain_script(answer)}

        if spoken_words(script.text) != spoken_words(answer):
            logger.warning("Voice director changed the words; speaking the answer as it stands")
            return {"voice_script": plain_script(answer)}
        cleaned = script.model_copy(update={"text": sanitize_tags(script.text)})
        return {"voice_script": cleaned}

    return voice_director_node
