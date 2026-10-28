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
    record_owner: str = "Mara"
    route_service_available: bool = True
    relay_status: str = "broken"
    repair_fuse_in_locker: bool = True
    player_has_fuse: bool = False
    family_release_card_valid: bool = True
    record_authorized: bool = False


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
    ALLOWED = {"inspect_route", "open_archive_door", "lookup_record",
               "inspect_public_lead", "inspect_relay", "take_repair_fuse",
               "repair_relay", "read_public_archive", "verify_release_card",
               "recover_final_recording"}

    @staticmethod
    def commit(turn: Turn, world: World, generation: int,
               quest_flags: set[str] | None = None) -> str:
        if turn.cancelled or turn.generation != generation:
            return "stale_turn"
        p = turn.proposal
        if p.tool not in ToolGate.ALLOWED:
            return "invalid_tool"
        if p.tool in {"inspect_public_lead", "verify_release_card", "recover_final_recording"}:
            if p.argument != "sister_final":
                return "invalid_target"
            if p.tool == "inspect_public_lead":
                turn.committed = True
                return "lead_found"
            if p.tool == "verify_release_card":
                if not world.family_release_card_valid:
                    return "invalid_release_card"
                world.record_authorized = True
                turn.committed = True
                return "authorized"
            if not world.record_authorized:
                return "authorization_required"
            if world.relay_status != "repaired" or not quest_flags or "evidence_complete" not in quest_flags:
                return "evidence_required"
            turn.committed = True
            return "recovered"
        if p.tool in {"inspect_relay", "take_repair_fuse", "repair_relay"}:
            if p.argument != "archive_relay":
                return "invalid_target"
            if p.tool == "inspect_relay":
                turn.committed = True
                return "fuse_fault" if world.relay_status == "broken" else "relay_stable"
            if p.tool == "take_repair_fuse":
                if not world.repair_fuse_in_locker:
                    return "fuse_unavailable"
                world.repair_fuse_in_locker = False
                world.player_has_fuse = True
                turn.committed = True
                return "fuse_taken"
            if not world.player_has_fuse:
                return "fuse_required"
            if world.relay_status == "repaired":
                return "already_repaired"
            world.player_has_fuse = False
            world.relay_status = "repaired"
            turn.committed = True
            return "repaired"
        if p.tool == "read_public_archive":
            if p.argument != "public_dispatch":
                return "invalid_target"
            if world.relay_status != "repaired":
                return "relay_offline"
            turn.committed = True
            return "public_entry"
        if p.tool == "lookup_record":
            if p.argument != "owner_note":
                return "invalid_target"
            turn.committed = True
            return world.record_owner
        if p.tool == "inspect_route":
            if p.argument not in {"east_bridge", "west_gallery"}:
                return "invalid_target"
            if not world.route_service_available:
                return "tool_unavailable"
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
