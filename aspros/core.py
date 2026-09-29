from __future__ import annotations

from pathlib import Path
from typing import Iterable

from aspros.connectors import ConnectorRegistry
from aspros.models import ActionResult, Capability, Device, DeviceAction, Scene
from aspros.storage import Storage


class AsprosCore:
    def __init__(self, database_path: Path) -> None:
        self.storage = Storage(database_path)
        self.connectors = ConnectorRegistry()
        self.devices = {device.id: device for device in self._default_devices()}
        self.scenes = {scene.id: scene for scene in self._default_scenes()}
        self._restore_states()

    def list_devices(self) -> list[dict]:
        return [device.to_dict() for device in self.devices.values()]

    def get_device(self, device_id: str) -> Device:
        try:
            return self.devices[device_id]
        except KeyError as error:
            raise ValueError(f"Appareil inconnu : {device_id}") from error

    def resolve_devices(self, query: str) -> list[Device]:
        normalized = _normalize(query)
        matches = []
        for device in self.devices.values():
            candidates = [device.id, device.name, *device.aliases]
            if any(_normalize(candidate) in normalized for candidate in candidates):
                matches.append(device)
        return matches

    def execute(self, action: DeviceAction) -> ActionResult:
        device = self.get_device(action.device_id)
        connector = self.connectors.get(device.connector)
        state, message = connector.execute(device, action)
        device.state = state
        self.storage.save_device_state(device.id, state)
        result = ActionResult(device.id, action.action, state, message)
        self.storage.log(action.source, "device_action", result.to_dict())
        return result

    def execute_many(self, actions: Iterable[DeviceAction]) -> list[ActionResult]:
        return [self.execute(action) for action in actions]

    def execute_scene(self, scene_id: str, source: str = "dashboard") -> list[ActionResult]:
        try:
            scene = self.scenes[scene_id]
        except KeyError as error:
            raise ValueError(f"Scène inconnue : {scene_id}") from error
        results = self.execute_many(
            DeviceAction(action.device_id, action.action, action.parameters, source)
            for action in scene.actions
        )
        self.storage.log(source, "scene_executed", {"scene_id": scene.id, "name": scene.name})
        return results

    def list_scenes(self) -> list[dict]:
        return [scene.to_dict() for scene in self.scenes.values()]

    def audit(self, limit: int = 30) -> list[dict]:
        return self.storage.recent_logs(limit)

    def _restore_states(self) -> None:
        for device in self.devices.values():
            saved_state = self.storage.load_device_state(device.id)
            if saved_state is not None:
                device.state = saved_state

    @staticmethod
    def _default_devices() -> tuple[Device, ...]:
        light_capabilities = [Capability("turn_on"), Capability("turn_off"), Capability("set_brightness")]
        return (
            Device(
                id="lamp_desk",
                name="Lampe du bureau",
                kind="light",
                connector="simulated",
                capabilities=light_capabilities,
                state={"power": "off", "brightness": 70},
                aliases=["lampe bureau", "lampe du bureau", "bureau"],
            ),
            Device(
                id="lamp_living_room",
                name="Lampe du salon",
                kind="light",
                connector="simulated",
                capabilities=light_capabilities,
                state={"power": "off", "brightness": 60},
                aliases=["lampe salon", "lampe du salon", "salon"],
            ),
            Device(
                id="temperature_room",
                name="Capteur de température",
                kind="sensor",
                connector="simulated",
                capabilities=[Capability("read")],
                state={"temperature_celsius": 21.4, "battery": 86},
                aliases=["temperature", "capteur", "capteur de temperature"],
            ),
            Device(
                id="computer",
                name="Ordinateur principal",
                kind="computer",
                connector="simulated",
                capabilities=[Capability("turn_on"), Capability("turn_off"), Capability("lock"), Capability("unlock")],
                state={"power": "on", "locked": False},
                aliases=["ordinateur", "pc", "ordinateur principal"],
            ),
        )

    @staticmethod
    def _default_scenes() -> tuple[Scene, ...]:
        return (
            Scene(
                id="work_mode",
                name="Mode travail",
                description="Allume la lampe du bureau à 70 % et coupe celle du salon.",
                actions=(
                    DeviceAction("lamp_desk", "set_brightness", {"brightness": 70}),
                    DeviceAction("lamp_living_room", "turn_off"),
                ),
            ),
            Scene(
                id="night_mode",
                name="Mode nuit",
                description="Éteint les lumières et verrouille l'ordinateur.",
                actions=(
                    DeviceAction("lamp_desk", "turn_off"),
                    DeviceAction("lamp_living_room", "turn_off"),
                    DeviceAction("computer", "lock"),
                ),
            ),
            Scene(
                id="all_off",
                name="Tout éteindre",
                description="Éteint les appareils actuellement contrôlables.",
                actions=(
                    DeviceAction("lamp_desk", "turn_off"),
                    DeviceAction("lamp_living_room", "turn_off"),
                    DeviceAction("computer", "turn_off"),
                ),
            ),
        )


def _normalize(value: str) -> str:
    return (
        value.lower()
        .replace("é", "e")
        .replace("è", "e")
        .replace("ê", "e")
        .replace("à", "a")
        .replace("ù", "u")
        .replace("ô", "o")
        .replace("'", " ")
    )
