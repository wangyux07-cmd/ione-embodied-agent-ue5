# Failure analysis

These cases are expected weaknesses to preserve during review, not defects to hide.

## 1. Legal but semantically weak retrieval

`concern_focus` can satisfy `warn`, but it does not communicate a direction. If the dialogue says “avoid the eastern bridge,” a valid warning without `indicate_east` is incomplete. The library needs compound coverage or the scheduler must allow compatible gesture layering.

## 2. Occupied-hand fallback becomes vague

In `world_03`, holding an object correctly blocks hand gestures. The current fallback is `beat_small`, which is safe but does not communicate “I will signal through the beacon.” A face/eye or device-specific channel should be retrieved independently from body pose.

## 3. Finish-phrase can feel unresponsive

`firm_refusal` uses `finish_phrase`. If the player interrupts near the start, keeping the body pose while voice ownership changes may look like the NPC ignores the player. The acceptable phrase boundary must come from audio/viseme timing, not only montage duration.

## 4. Multi-anchor collisions

Long lines can schedule `enumerate_small` and `indicate_left` too closely. Both need the same upper-body slot and one can suppress the other. A production scheduler needs slot occupancy, transition cost and montage section metadata.

## 5. State tags can be stale

The planner receives a snapshot. If the character picks up an object after planning but before a gesture fires, `indicate_left` may no longer be legal. The executor should revalidate state at the fire boundary and choose a pre-authored fallback.

## 6. Static key art overstates visual completeness

The web surrogate uses polished generated key art, but it does not prove a consistent turnaround, topology, rig, eye shader, cloth setup or animation quality. Those are separate asset milestones and must be shown from UE viewport captures before portfolio claims change.
