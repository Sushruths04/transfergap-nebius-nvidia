"""Contracts for integration, not robot drivers or evidence of compatibility."""
from dataclasses import dataclass
from typing import Protocol

from .metrics import finite_number


@dataclass(frozen=True)
class RobotSpec:
    robot_id: str
    embodiment_tag: str
    action_names: tuple[str, ...]
    frame_id: str
    control_hz: float
    asset_revision: str
    policy_revision: str

    def validate(self):
        if not all((self.robot_id, self.embodiment_tag, self.frame_id, self.asset_revision, self.policy_revision)):
            raise ValueError("Robot, asset and policy identities and coordinate frame are required")
        if not self.action_names or len(set(self.action_names)) != len(self.action_names):
            raise ValueError("Action names must be nonempty and unique")
        if not finite_number(self.control_hz) or self.control_hz <= 0:
            raise ValueError("control_hz must be positive")


def validate_action_chunk(spec, chunk):
    spec.validate()
    if not chunk:
        raise ValueError("Empty action chunk")
    for action in chunk:
        if len(action) != len(spec.action_names) or not all(map(finite_number, action)):
            raise ValueError(f"Expected finite {len(spec.action_names)}D actions for {spec.embodiment_tag}")


def sonic_action_names():
    # Current N1.7 SONIC representation. Not the legacy 14D wrist interface.
    return tuple([f"motion_token_{i}" for i in range(64)]
                 + [f"left_hand_{i}" for i in range(7)] + [f"right_hand_{i}" for i in range(7)])


class RobotAdapter(Protocol):
    spec: RobotSpec

    def reset(self, scene_id: str, seed: int) -> dict: ...
    def observe(self) -> dict: ...
    def execute(self, action_chunk: list[list[float]]) -> None: ...
    def ground_truth(self) -> dict: ...
    def stop(self) -> None: ...


def validate_plan(plan, allowed_skills):
    """Validate a Nemotron proposal before handing it to a skill executor."""
    if not isinstance(plan, dict):
        raise ValueError("Plan must be a JSON object")
    steps = plan.get("steps")
    if not isinstance(steps, list) or not steps or len(steps) > 20:
        raise ValueError("Plan must have 1–20 steps")
    for step in steps:
        if not isinstance(step, dict) or step.get("skill") not in allowed_skills:
            raise ValueError("Plan contains an unsupported robot skill")
        if not isinstance(step.get("target"), str) or not step["target"]:
            raise ValueError("Every step requires a target")
    return plan
