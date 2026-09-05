"""Pure score-change tracking for watched-team display events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SCORE_SETTLE_SECONDS = 25
CONVERSION_WINDOW_SECONDS = 120


@dataclass
class TeamScoreState:
    event_id: str
    observed_score: int
    announced_score: int
    pending_score: int | None = None
    pending_since: float | None = None
    last_emit_at: float | None = None
    last_emit_delta: int = 0


class SportsScoreTracker:
    """Debounce scores and suppress post-touchdown conversion-only changes."""

    def __init__(self) -> None:
        self._teams: dict[str, TeamScoreState] = {}

    def update(self, games: list[dict[str, Any]], now: float) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for game in games:
            key = str(game["key"])
            event_id = str(game["eventId"])
            score = max(0, int(game.get("score", 0)))
            state = self._teams.get(key)

            if state is None or state.event_id != event_id:
                self._teams[key] = TeamScoreState(event_id, score, score)
                continue

            if game.get("state") != "in" or game.get("completed"):
                state.observed_score = score
                state.announced_score = score
                state.pending_score = None
                state.pending_since = None
                continue

            if score < state.observed_score:
                state.observed_score = score
                state.announced_score = min(state.announced_score, score)
                state.pending_score = None
                state.pending_since = None
                continue

            if score > state.observed_score:
                increase = score - state.observed_score
                state.observed_score = score
                recent_touchdown = (
                    state.last_emit_at is not None
                    and now - state.last_emit_at <= CONVERSION_WINDOW_SECONDS
                    and state.last_emit_delta >= 6
                )
                if increase <= 2 and recent_touchdown:
                    state.announced_score = score
                    state.pending_score = None
                    state.pending_since = None
                    continue
                if state.pending_score is None:
                    state.pending_since = now
                state.pending_score = score

            if (
                state.pending_score is not None
                and state.pending_since is not None
                and now - state.pending_since >= SCORE_SETTLE_SECONDS
            ):
                delta = state.pending_score - state.announced_score
                if delta > 0:
                    events.append({
                        **game,
                        "previousScore": state.announced_score,
                        "score": state.pending_score,
                        "scoreIncrease": delta,
                    })
                    state.announced_score = state.pending_score
                    state.last_emit_at = now
                    state.last_emit_delta = delta
                state.pending_score = None
                state.pending_since = None

        return events
