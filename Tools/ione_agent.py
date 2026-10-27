"""Offline, deterministic world-grounded agent harness.

This is an executable contract and evaluation fixture, not an LLM adapter.
No action mutates world state until ToolGate.commit succeeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Strategy = Literal["dialogue", "tool", "embodied"]


@dataclass
class World:
    east_bridge: str = "collapsed"
    west_gallery: str = "open"
    archive_door: str = "locked"
    owner_consent: bool = False


@dataclass
class Proposal:
    dialogue: str
    tool: str | None = None
    argument: str | None = None
    gesture: str | None = None
    fork_state: str = "listening"


@dataclass
class Turn:
    generation: int
    proposal: Proposal
    committed: bool = False
    cancelled: bool = False
    events: list[str] = field(default_factory=list)


class ToolGate:
    ALLOWED = {"inspect_route", "open_archive_door"}

    @staticmethod
    def commit(turn: Turn, world: World, generation: int) -> str:
        if turn.cancelled or turn.generation != generation:
            return "stale_turn"
        p = turn.proposal
        if p.tool not in ToolGate.ALLOWED:
            return "invalid_tool"
        if p.tool == "inspect_route":
            if p.argument not in {"east_bridge", "west_gallery"}:
                return "invalid_target"
            turn.committed = True
            return getattr(world, p.argument)
        if p.argument != "archive_door":
            return "invalid_target"
        if not world.owner_consent:
            return "consent_required"
        if world.archive_door != "locked":
            return "door_not_locked"
        world.archive_door = "open"
        turn.committed = True
        return "opened"


class IoneHarness:
    def __init__(self, world: World | None = None):
        self.world = world or World()
        self.generation = 0
        self.active: Turn | None = None
        self.memory: list[str] = []

    def propose(self, user_text: str, strategy: Strategy) -> Turn:
        self.generation += 1
        message = user_text.lower()
        if "open" in message and ("record" in message or "door" in message):
            if strategy == "dialogue":
                p = Proposal("I can open the archive for you.")
            else:
                p = Proposal("I need the record owner's consent before opening it.",
                             "open_archive_door", "archive_door")
        elif "bridge" in message or "route" in message:
            if strategy == "dialogue":
                p = Proposal("The east bridge should be safe. Follow me.")
            else:
                p = Proposal("I will inspect the east bridge before suggesting a route.",
                             "inspect_route", "east_bridge")
        else:
            p = Proposal("Tell me which part of the archive you need.")
        if strategy == "embodied":
            p.gesture = "indicate_east" if p.tool == "inspect_route" else "listen_small"
            p.fork_state = "planning" if p.tool else "listening"
        self.active = Turn(self.generation, p, events=["proposal_created"])
        return self.active

    def execute(self, turn: Turn) -> str:
        if not turn.proposal.tool:
            return "no_tool"
        result = ToolGate.commit(turn, self.world, self.generation)
        turn.events.append(f"tool:{result}")
        if result == "collapsed":
            turn.proposal.dialogue = "The east bridge has collapsed. Use the west gallery."
        if result == "opened":
            self.memory.append("archive_door_opened_with_consent")
        if result == "consent_required":
            turn.proposal.dialogue = "The record stays sealed until its owner consents."
        if turn.proposal.fork_state == "planning":
            turn.proposal.fork_state = "tool_complete"
        return result

    def interrupt(self) -> None:
        self.generation += 1
        if self.active:
            self.active.cancelled = True
            self.active.events.append("interrupted")
            self.active.proposal.fork_state = "listening"
            self.active.proposal.gesture = None
