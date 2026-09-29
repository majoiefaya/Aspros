import tempfile
import unittest
from pathlib import Path

from aspros.commands import CommandInterpreter
from aspros.core import AsprosCore
from aspros.models import DeviceAction


class AsprosCoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.core = AsprosCore(Path(self.temporary_directory.name) / "aspros.db")
        self.interpreter = CommandInterpreter(self.core)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_text_command_turns_on_desk_light(self) -> None:
        response = self.interpreter.interpret("allume la lampe du bureau")
        self.assertEqual(response.intent, "turn_on")
        self.assertEqual(self.core.get_device("lamp_desk").state["power"], "on")

    def test_brightness_command_updates_light(self) -> None:
        self.interpreter.interpret("règle la lampe du bureau à 42 %")
        state = self.core.get_device("lamp_desk").state
        self.assertEqual(state["brightness"], 42)
        self.assertEqual(state["power"], "on")

    def test_work_scene_executes_multiple_actions(self) -> None:
        results = self.core.execute_scene("work_mode")
        self.assertEqual(len(results), 2)
        self.assertEqual(self.core.get_device("lamp_desk").state["brightness"], 70)
        self.assertEqual(self.core.get_device("lamp_living_room").state["power"], "off")

    def test_invalid_action_is_rejected(self) -> None:
        with self.assertRaises(Exception):
            self.core.execute(DeviceAction("temperature_room", "turn_on"))


if __name__ == "__main__":
    unittest.main()
