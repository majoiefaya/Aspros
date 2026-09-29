from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Capability:
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Device:
    id: str
    name: str
    kind: str
    connector: str
    capabilities: list[Capability]
    state: dict[str, Any]
    aliases: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "connector": self.connector,
            "capabilities": [capability.to_dict() for capability in self.capabilities],
            "state": self.state,
            "aliases": self.aliases,
        }


@dataclass(frozen=True)
class DeviceAction:
    device_id: str
    action: str
    parameters: dict[str, Any] = field(default_factory=dict)
    source: str = "dashboard"


@dataclass(frozen=True)
class ActionResult:
    device_id: str
    action: str
    state: dict[str, Any]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Scene:
    id: str
    name: str
    description: str
    actions: tuple[DeviceAction, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "actions": [asdict(action) for action in self.actions],
        }
