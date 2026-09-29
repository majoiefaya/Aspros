from __future__ import annotations

import re
from dataclasses import dataclass

from aspros.core import AsprosCore, _normalize
from aspros.models import DeviceAction


@dataclass(frozen=True)
class CommandResponse:
    message: str
    results: list[dict]
    intent: str

    def to_dict(self) -> dict:
        return {"message": self.message, "results": self.results, "intent": self.intent}


class CommandInterpreter:
    def __init__(self, core: AsprosCore) -> None:
        self.core = core

    def interpret(self, text: str, source: str = "text") -> CommandResponse:
        normalized = _normalize(text).strip()
        if not normalized:
            raise ValueError("La commande ne peut pas être vide.")

        scene = self._match_scene(normalized)
        if scene:
            results = self.core.execute_scene(scene, source)
            return CommandResponse(
                f"Scène « {self.core.scenes[scene].name} » exécutée.",
                [result.to_dict() for result in results],
                "execute_scene",
            )

        if any(word in normalized for word in ("etat", "statut", "appareils", "appareil")):
            devices = self.core.list_devices()
            return CommandResponse("Voici les appareils connus.", devices, "list_devices")

        target_devices = self.core.resolve_devices(normalized)
        if not target_devices and any(word in normalized for word in ("lampe", "lumieres", "lumiere")):
            target_devices = [device for device in self.core.devices.values() if device.kind == "light"]
        if not target_devices:
            raise ValueError("Je n'ai pas reconnu l'appareil à contrôler.")

        action, parameters = self._extract_action(normalized)
        results = self.core.execute_many(
            DeviceAction(device.id, action, parameters, source) for device in target_devices
        )
        return CommandResponse(
            " ".join(result.message for result in results),
            [result.to_dict() for result in results],
            action,
        )

    def _match_scene(self, text: str) -> str | None:
        aliases = {
            "work_mode": ("mode travail", "travail"),
            "night_mode": ("mode nuit", "bonne nuit", "dormir"),
            "all_off": ("tout eteindre", "eteins tout", "eteindre tout"),
        }
        for scene_id, words in aliases.items():
            if any(word in text for word in words):
                return scene_id
        return None

    @staticmethod
    def _extract_action(text: str) -> tuple[str, dict]:
        brightness = re.search(r"(?:a|à)\s*(\d{1,3})\s*%?", text)
        if any(word in text for word in ("luminosite", "regle", "regler", "mets")) and brightness:
            value = int(brightness.group(1))
            if not 0 <= value <= 100:
                raise ValueError("La luminosité doit être comprise entre 0 et 100 %.")
            return "set_brightness", {"brightness": value}
        if any(word in text for word in ("allume", "demarre", "active", "allumer")):
            return "turn_on", {}
        if any(word in text for word in ("eteins", "eteindre", "coupe", "arrete", "arreter")):
            return "turn_off", {}
        if any(word in text for word in ("verrouille", "verrouiller")):
            return "lock", {}
        if any(word in text for word in ("deverrouille", "deverrouiller")):
            return "unlock", {}
        if any(word in text for word in ("temperature", "lire", "mesure")):
            return "read", {}
        raise ValueError("Je comprends l'appareil, mais pas encore l'action demandée.")
