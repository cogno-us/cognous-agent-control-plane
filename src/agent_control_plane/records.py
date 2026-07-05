"""Run recorder – accumulates run state and produces RunRecord / ReplayBundle.

:class:`RunRecorder` is the main entry point for instrumenting an agent run.
It wraps :class:`~agent_control_plane.policy_gate.PolicyGate` and collects
all events into an in-memory :class:`~agent_control_plane.models.RunRecord`
that can be exported to JSON or converted to a
:class:`~agent_control_plane.models.ReplayBundle`.
"""

from __future__ import annotations

import json
import pathlib
import uuid
from typing import Optional

from agent_control_plane.frame import create_frame
from agent_control_plane.models import (
    ActionProposal,
    AuthorityRecord,
    BlockedAction,
    Frame,
    PolicyDecision,
    PolicyEvaluationTrace,
    RelianceRecord,
    ReplayBundle,
    RunRecord,
)
from agent_control_plane.policy_gate import PolicyGate
from agent_control_plane.replay import generate_replay_bundle


class RunRecorder:
    """Records a single agent run and evaluates proposed actions via a policy gate.

    Usage::

        recorder = RunRecorder()
        recorder.start_run(
            task="Summarise customer record",
            actor="agent-v1",
            environment="production",
            allowed_tools=["crm_read"],
            blocked_tools=["email_send"],
            policy_version="v1.0",
        )
        action = recorder.propose_action(
            tool_name="crm_read",
            action_type="read",
            target="customer:123",
            payload={"fields": ["name", "email"]},
        )
        decision = recorder.evaluate_action(action)
        recorder.record_reliance(
            source_name="crm_read",
            source_type="tool",
            scope="customer record fields",
            referenced_action_id=action.action_id,
        )
        recorder.complete_run("Summary produced.")
        run_record = recorder.to_run_record()
        recorder.export_json("run_output.json")
    """

    def __init__(self, gate: Optional[PolicyGate] = None) -> None:
        self._gate = gate or PolicyGate()
        self._run_id: Optional[str] = None
        self._task: Optional[str] = None
        self._created_at: Optional[str] = None
        self._frame: Optional[Frame] = None
        self._actions: list[ActionProposal] = []
        self._decisions: list[PolicyDecision] = []
        self._policy_traces: list[PolicyEvaluationTrace] = []
        self._authority_records: list[AuthorityRecord] = []
        self._reliance_records: list[RelianceRecord] = []
        self._blocked_actions: list[BlockedAction] = []
        self._completed: bool = False
        self._final_output: Optional[str] = None
        self._replay_bundle_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Run lifecycle
    # ------------------------------------------------------------------

    def start_run(
        self,
        *,
        task: str,
        actor: str,
        environment: str,
        allowed_tools: list[str],
        blocked_tools: list[str],
        policy_version: str,
    ) -> str:
        """Initialise a new run and return the ``run_id``.

        Args:
            task: Human-readable description of the task.
            actor: Identifier of the agent or user.
            environment: Deployment environment string.
            allowed_tools: Tools that are permitted in this run.
            blocked_tools: Tools that are explicitly blocked.
            policy_version: Version string of the active policy set.

        Returns:
            The ``run_id`` for the new run.
        """
        self._run_id = str(uuid.uuid4())
        self._task = task
        self._frame = create_frame(
            task=task,
            actor=actor,
            environment=environment,
            allowed_tools=allowed_tools,
            blocked_tools=blocked_tools,
            policy_version=policy_version,
        )
        self._created_at = self._frame.created_at
        return self._run_id

    def add_authority_record(
        self,
        *,
        actor: str,
        scope: list[str],
        source: str,
        expires_at: Optional[str] = None,
    ) -> AuthorityRecord:
        """Add an authority record to the current run.

        Args:
            actor: The actor being granted authority.
            scope: List of permission scopes, e.g. ``["read", "write"]``.
            source: Where the authority was granted from.
            expires_at: Optional ISO-8601 expiry timestamp.

        Returns:
            The created :class:`~agent_control_plane.models.AuthorityRecord`.
        """
        self._require_started()
        record = AuthorityRecord(
            authority_id=str(uuid.uuid4()),
            run_id=self._run_id,  # type: ignore[arg-type]
            actor=actor,
            scope=scope,
            source=source,
            expires_at=expires_at,
        )
        self._authority_records.append(record)
        return record

    def propose_action(
        self,
        *,
        tool_name: str,
        action_type: str,
        target: str,
        payload: Optional[dict] = None,
        reason: Optional[str] = None,
    ) -> ActionProposal:
        """Record a proposed action and return the :class:`~agent_control_plane.models.ActionProposal`.

        The action is only recorded here; use :meth:`evaluate_action` to run
        it through the policy gate.

        Args:
            tool_name: Name of the tool the agent wants to call.
            action_type: Semantic type, e.g. ``"read"``, ``"write"``, ``"external_send"``.
            target: Resource or endpoint the action targets.
            payload: Optional arguments to pass to the tool.
            reason: Optional agent-supplied justification.

        Returns:
            The created :class:`~agent_control_plane.models.ActionProposal`.
        """
        self._require_started()
        proposal = ActionProposal(
            action_id=str(uuid.uuid4()),
            run_id=self._run_id,  # type: ignore[arg-type]
            tool_name=tool_name,
            action_type=action_type,
            target=target,
            payload=payload or {},
            reason=reason,
        )
        self._actions.append(proposal)
        return proposal

    def evaluate_action(
        self,
        action: ActionProposal,
        include_trace: bool = True,
    ) -> tuple[PolicyDecision, Optional[BlockedAction]]:
        """Run the action proposal through the policy gate.

        If the decision is ``"block"``, a :class:`~agent_control_plane.models.BlockedAction`
        record is automatically created and added to the run.

        Args:
            action: The proposal to evaluate (must have been produced by
                :meth:`propose_action` for the current run).

        Returns:
            A 2-tuple of ``(PolicyDecision, Optional[BlockedAction])``.
            The :class:`~agent_control_plane.models.BlockedAction` is ``None`` for
            non-blocking decisions.
        """
        self._require_started()
        if action.run_id != self._run_id:
            raise ValueError("Action belongs to a different run.")
        if not any(proposed.action_id == action.action_id for proposed in self._actions):
            raise ValueError("Action was not proposed in this run.")
        if include_trace:
            decision, trace = self._gate.evaluate_with_trace(  # type: ignore[arg-type]
                action,
                self._frame,
                self._authority_records,
            )
            self._policy_traces.append(trace)
        else:
            decision = self._gate.evaluate(  # type: ignore[arg-type]
                action,
                self._frame,
                self._authority_records,
            )
        self._decisions.append(decision)

        blocked: Optional[BlockedAction] = None
        if decision.result == "block":
            blocked = BlockedAction(
                blocked_id=str(uuid.uuid4()),
                action_id=action.action_id,
                run_id=self._run_id,  # type: ignore[arg-type]
                reason=decision.reason,
                policy_name=decision.policy_name,
            )
            self._blocked_actions.append(blocked)

        return decision, blocked

    def get_policy_traces(self) -> list[PolicyEvaluationTrace]:
        """Return a copy of the recorded policy traces."""

        return list(self._policy_traces)

    def record_reliance(
        self,
        *,
        source_name: str,
        source_type: str,
        scope: str,
        referenced_action_id: Optional[str] = None,
    ) -> RelianceRecord:
        """Record an external-source reliance for the current run.

        Args:
            source_name: Name of the tool, database, or other source.
            source_type: One of ``"tool"``, ``"database"``, ``"file"``,
                ``"api"``, ``"user_input"``, ``"model_output"``, ``"other"``.
            scope: Description of what was accessed.
            referenced_action_id: Optional ``action_id`` that triggered this reliance.

        Returns:
            The created :class:`~agent_control_plane.models.RelianceRecord`.
        """
        self._require_started()
        record = RelianceRecord(
            reliance_id=str(uuid.uuid4()),
            run_id=self._run_id,  # type: ignore[arg-type]
            source_name=source_name,
            source_type=source_type,  # type: ignore[arg-type]
            scope=scope,
            referenced_action_id=referenced_action_id,
        )
        self._reliance_records.append(record)
        return record

    def complete_run(self, final_output: Optional[str] = None) -> None:
        """Mark the run as completed and record the final output.

        Args:
            final_output: Optional string output produced by the agent.
        """
        self._require_started()
        self._completed = True
        self._final_output = final_output

    def to_run_record(self) -> RunRecord:
        """Return a :class:`~agent_control_plane.models.RunRecord` snapshot of this run.

        Returns:
            A :class:`RunRecord` containing all events recorded so far.
        """
        self._require_started()
        return RunRecord(
            run_id=self._run_id,  # type: ignore[arg-type]
            task=self._task,  # type: ignore[arg-type]
            created_at=self._created_at,  # type: ignore[arg-type]
            frame=self._frame,  # type: ignore[arg-type]
            actions=list(self._actions),
            decisions=list(self._decisions),
            policy_traces=list(self._policy_traces),
            authority_records=list(self._authority_records),
            reliance_records=list(self._reliance_records),
            blocked_actions=list(self._blocked_actions),
            completed=self._completed,
            final_output=self._final_output,
            replay_bundle_id=self._replay_bundle_id,
        )

    def export_json(self, path: str | pathlib.Path) -> pathlib.Path:
        """Export the current run record to a JSON file.

        Args:
            path: File path to write to.  Parent directories are created
                automatically if they do not exist.

        Returns:
            The resolved :class:`~pathlib.Path` that was written.
        """
        out = pathlib.Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        run_record = self.to_run_record()
        out.write_text(
            json.dumps(run_record.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return out

    def generate_replay_bundle(self) -> ReplayBundle:
        """Generate a :class:`~agent_control_plane.models.ReplayBundle` for this run.

        The bundle is self-contained and includes all data required to
        replay or audit the run.  The ``replay_bundle_id`` is stored on
        the recorder so subsequent calls to :meth:`to_run_record` include it.

        Returns:
            A :class:`ReplayBundle` instance.
        """
        run_record = self.to_run_record()
        bundle = generate_replay_bundle(run_record)
        self._replay_bundle_id = bundle.replay_bundle_id
        return bundle

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _require_started(self) -> None:
        if self._run_id is None:
            raise RuntimeError(
                "Run has not been started.  Call start_run() first."
            )
