from __future__ import annotations

from abc import ABC, abstractmethod

from aspros.models import Device, DeviceAction


class ConnectorError(Exception):
    pass


class DeviceConnector(ABC):
    """Contrat à respecter par MQTT, Home Assistant, Bluetooth, etc."""

    @abstractmethod
    def execute(self, device: Device, command: DeviceAction) -> tuple[dict, str]:
        """Retourne le nouvel état et un message pour l'utilisateur."""


class SimulatedConnector(DeviceConnector):
    """Connecteur de développement : son comportement reproduit un appareil."""

    def execute(self, device: Device, command: DeviceAction) -> tuple[dict, str]:
        allowed = {capability.name for capability in device.capabilities}
        if command.action not in allowed:
            raise ConnectorError(
                f"L'action '{command.action}' n'est pas disponible pour {device.name}."
            )

        state = dict(device.state)
        if command.action == "turn_on":
            state["power"] = "on"
            message = f"{device.name} est allumé."
        elif command.action == "turn_off":
            state["power"] = "off"
            message = f"{device.name} est éteint."
        elif command.action == "set_brightness":
            brightness = command.parameters.get("brightness")
            if not isinstance(brightness, int) or not 0 <= brightness <= 100:
                raise ConnectorError("La luminosité doit être un entier entre 0 et 100.")
            state["power"] = "on" if brightness > 0 else "off"
            state["brightness"] = brightness
            message = f"La luminosité de {device.name} est réglée à {brightness} %."
        elif command.action == "read":
            message = f"État de {device.name} récupéré."
        elif command.action == "lock":
            state["locked"] = True
            message = f"{device.name} est verrouillé."
        elif command.action == "unlock":
            state["locked"] = False
            message = f"{device.name} est déverrouillé."
        else:
            raise ConnectorError(f"Action inconnue : {command.action}")
        return state, message


class ConnectorRegistry:
    def __init__(self) -> None:
        self._connectors: dict[str, DeviceConnector] = {"simulated": SimulatedConnector()}

    def register(self, name: str, connector: DeviceConnector) -> None:
        self._connectors[name] = connector

    def get(self, name: str) -> DeviceConnector:
        try:
            return self._connectors[name]
        except KeyError as error:
            raise ConnectorError(f"Connecteur indisponible : {name}") from error
