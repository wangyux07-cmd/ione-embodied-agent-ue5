"""Verified fact anchors for expressive NPC replies.

The LLM may add character voice; only the tool layer owns game facts and pose intent.
"""

from __future__ import annotations

from dataclasses import dataclass

from ione_agent import World
from ione_llm import ResponseOutput

SAFE_SUFFIXES = frozenset({
    "", "Careful now.", "Stay close.", "Take your time.", "I'm listening.",
    "I wish I had better news.", "Let's think this through.",
})

@dataclass(frozen=True)
class FactCard:
    sentence: str
    expression: str
    tool: str
    target: str
    result: str


def make_fact_card(tool: str, target: str, result: str, world: World) -> FactCard:
    label = target.replace("_", " ")
    if tool == "inspect_route":
        if result == "collapsed":
            sentence = f"The {label} has collapsed."
            if target == "east_bridge" and world.west_gallery == "open":
                sentence += " The west gallery is open."
            elif target == "east_bridge" and world.west_gallery == "collapsed":
                sentence += " The west gallery has also collapsed."
            return FactCard(sentence, "warning", tool, target, result)
        if result == "open":
            return FactCard(f"The {label} is open.", "speaking", tool, target, result)
        if result == "tool_unavailable":
            return FactCard(f"I cannot verify the {label} because the map service is unavailable.",
                            "warning", tool, target, result)
    if tool == "open_archive_door":
        if result == "consent_required":
            return FactCard("The archive door remains locked. I cannot open it without the owner's consent.",
                            "warning", tool, target, result)
        if result == "opened":
            return FactCard("The archive door is open.", "speaking", tool, target, result)
        if result == "door_not_locked":
            return FactCard("The archive door was already open.", "speaking", tool, target, result)
    if tool == "lookup_record" and target == "owner_note":
        return FactCard(f"The red ledger belongs to {result}.", "speaking", tool, target, result)
    raise ValueError(f"unsupported fact card: {tool}/{target}/{result}")


def publish_response(response: ResponseOutput, card: FactCard) -> tuple[str, str, str]:
    """Accept a characterful reply only when the verified sentence is preserved.

    The suffix may express Ione's voice, but cannot add unsupported game facts.
    Returns final text, authoritative pose, and acceptance/fallback reason.
    """
    reply = response.reply.strip()
    if not reply.casefold().startswith(card.sentence.casefold()):
        return card.sentence, card.expression, "missing_fact_anchor"
    suffix = reply[len(card.sentence):].strip()
    if suffix not in SAFE_SUFFIXES:
        return card.sentence, card.expression, "unapproved_character_line"
    return reply, card.expression, "model_accepted"
