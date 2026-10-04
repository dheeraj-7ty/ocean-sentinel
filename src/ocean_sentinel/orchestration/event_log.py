"""Durable Event Log for Investigation Runs (Phase 7B).

Provides append-only, newline-delimited JSON (JSONL) storage for investigation events
under outputs/investigations/<run_id>/events.jsonl.

Guarantees:
- Monotonic sequence persistence across process restarts
- Append-only local filesystem writes with immediate flushing
- Safe recovery from incomplete/corrupted trailing records
- Linear replay from a specified sequence cursor
- Strict isolation per investigation run
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from ocean_sentinel.orchestration.events import (
    EventSeverity,
    InvestigationEvent,
    InvestigationEventType,
)

logger = logging.getLogger(__name__)


class DurableEventLogError(Exception):
    """Base error for durable event log operations."""


class DurableEventLog:
    """Manages append-only event persistence for an individual investigation run."""

    def __init__(self, log_path: Path) -> None:
        self.log_path = Path(log_path).resolve()
        self.run_id = self.log_path.parent.name
        self._current_sequence = 0
        self._corrupted_records_count = 0
        self._initialize_log()

    @property
    def current_sequence(self) -> int:
        """The highest durable sequence number recorded."""
        return self._current_sequence

    def get_latest_sequence(self) -> int:
        """Return the latest sequence number written to the event log."""
        return self._current_sequence

    @property
    def corrupted_records_count(self) -> int:
        """Count of malformed trailing records skipped during recovery."""
        return self._corrupted_records_count

    def _initialize_log(self) -> None:
        """Scan existing log file, recover latest sequence, and handle partial records."""
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self._current_sequence = 0
            return

        highest_seq = 0
        valid_lines: List[str] = []
        has_trailing_corruption = False

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                    evt = InvestigationEvent.from_dict(data)
                    if evt.sequence > highest_seq:
                        highest_seq = evt.sequence
                    valid_lines.append(clean_line)
                except Exception as err:
                    logger.warning(
                        "Malformed record in event log '%s' at line %d: %s. Truncating trailing corruption.",
                        self.log_path,
                        line_no,
                        err,
                    )
                    self._corrupted_records_count += 1
                    has_trailing_corruption = True

        self._current_sequence = highest_seq

        # If trailing corruption was detected, clean up by rewriting only valid records
        if has_trailing_corruption:
            logger.info(
                "Remediating corrupted event log for run '%s'. Preserving %d valid events.",
                self.run_id,
                len(valid_lines),
            )
            tmp_path = self.log_path.with_suffix(".tmp_recover")
            with open(tmp_path, "w", encoding="utf-8") as f:
                for v in valid_lines:
                    f.write(v + "\n")
            tmp_path.replace(self.log_path)

    def append(self, event: InvestigationEvent) -> None:
        """Append an event to the durable log with immediate flush."""
        if event.run_id != self.run_id:
            raise DurableEventLogError(
                f"Cannot append event for run '{event.run_id}' into log for run '{self.run_id}'."
            )
        if event.sequence <= self._current_sequence:
            raise DurableEventLogError(
                f"Sequence violation: event sequence {event.sequence} is not strictly greater "
                f"than current log sequence {self._current_sequence}."
            )

        line = event.to_json() + "\n"
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)
            f.flush()

        self._current_sequence = event.sequence

    def emit(
        self,
        event_type: Union[InvestigationEventType, str],
        payload: Optional[Dict[str, Any]] = None,
        stage_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        producer: str = "InvestigationEngine",
        severity: Union[EventSeverity, str] = EventSeverity.INFO,
        correlation_id: Optional[str] = None,
    ) -> InvestigationEvent:
        """Helper to create, serialize, and append an event atomically in sequence."""
        next_seq = self._current_sequence + 1
        evt = InvestigationEvent.create(
            run_id=self.run_id,
            sequence=next_seq,
            event_type=event_type,
            payload=payload or {},
            stage_id=stage_id,
            attempt_id=attempt_id,
            producer=producer,
            severity=severity,
            correlation_id=correlation_id,
        )
        self.append(evt)
        return evt

    def replay(
        self,
        after_sequence: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[InvestigationEvent]:
        """Read and replay historical events recorded in the log."""
        if not self.log_path.exists():
            return []

        min_seq = after_sequence if after_sequence is not None else 0
        events: List[InvestigationEvent] = []

        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                    evt = InvestigationEvent.from_dict(data)
                    if evt.sequence > min_seq:
                        events.append(evt)
                        if limit and len(events) >= limit:
                            break
                except Exception as err:
                    logger.error(
                        "Error reading event log line in '%s': %s", self.log_path, err
                    )

        return events

    def iter_events(self, after_sequence: Optional[int] = None) -> Iterator[InvestigationEvent]:
        """Stream historical events lazily without loading the entire log into memory."""
        if not self.log_path.exists():
            return

        min_seq = after_sequence if after_sequence is not None else 0
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                clean_line = line.strip()
                if not clean_line:
                    continue
                try:
                    data = json.loads(clean_line)
                    evt = InvestigationEvent.from_dict(data)
                    if evt.sequence > min_seq:
                        yield evt
                except Exception as err:
                    logger.error("Error reading event during stream iteration: %s", err)
