from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from aspros.commands import CommandInterpreter
from aspros.connectors import ConnectorError
from aspros.core import AsprosCore
from aspros.models import DeviceAction


ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
DATA = ROOT.parent / "data" / "aspros.db"


class AsprosHandler(BaseHTTPRequestHandler):
    core: AsprosCore
    interpreter: CommandInterpreter

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/health":
            return self._json({"status": "ok", "service": "ASPROS", "version": "0.1.0"})
        if path == "/api/devices":
            return self._json({"devices": self.core.list_devices()})
        if path == "/api/scenes":
            return self._json({"scenes": self.core.list_scenes()})
        if path == "/api/audit":
            return self._json({"events": self.core.audit()})
        if path == "/" or path == "/index.html":
            return self._file(STATIC / "index.html", "text/html; charset=utf-8")
        if path == "/app.js":
            return self._file(STATIC / "app.js", "application/javascript; charset=utf-8")
        if path == "/styles.css":
            return self._file(STATIC / "styles.css", "text/css; charset=utf-8")
        self._error(HTTPStatus.NOT_FOUND, "Route introuvable.")

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            payload = self._body_json()
            if path == "/api/commands":
                text = payload.get("text")
                if not isinstance(text, str):
                    raise ValueError("Le champ 'text' est obligatoire.")
                return self._json(self.interpreter.interpret(text).to_dict())
            if path.startswith("/api/scenes/") and path.endswith("/execute"):
                scene_id = unquote(path.removeprefix("/api/scenes/").removesuffix("/execute").strip("/"))
                results = self.core.execute_scene(scene_id)
                return self._json({"results": [result.to_dict() for result in results]})
            if path.startswith("/api/devices/") and path.endswith("/actions"):
                device_id = unquote(path.removeprefix("/api/devices/").removesuffix("/actions").strip("/"))
                action = payload.get("action")
                if not isinstance(action, str):
                    raise ValueError("Le champ 'action' est obligatoire.")
                parameters = payload.get("parameters", {})
                if not isinstance(parameters, dict):
                    raise ValueError("'parameters' doit être un objet JSON.")
                result = self.core.execute(DeviceAction(device_id, action, parameters))
                return self._json(result.to_dict())
            self._error(HTTPStatus.NOT_FOUND, "Route introuvable.")
        except (ValueError, ConnectorError, json.JSONDecodeError) as error:
            self._error(HTTPStatus.BAD_REQUEST, str(error))

    def _body_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("Requête trop volumineuse.")
        content = self.rfile.read(length).decode("utf-8")
        body = json.loads(content or "{}")
        if not isinstance(body, dict):
            raise ValueError("Le corps doit être un objet JSON.")
        return body

    def _json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _file(self, file_path: Path, content_type: str) -> None:
        if not file_path.is_file():
            return self._error(HTTPStatus.NOT_FOUND, "Fichier introuvable.")
        encoded = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _error(self, status: HTTPStatus, message: str) -> None:
        self._json({"error": message}, status)

    def log_message(self, format: str, *args) -> None:  # noqa: A002
        return


def run(port: int) -> None:
    AsprosHandler.core = AsprosCore(DATA)
    AsprosHandler.interpreter = CommandInterpreter(AsprosHandler.core)
    server = ThreadingHTTPServer(("127.0.0.1", port), AsprosHandler)
    print(f"ASPROS est prêt sur http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nASPROS est arrêté.")
    finally:
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Démarre le MVP local d'ASPROS.")
    parser.add_argument("--port", type=int, default=8765)
    run(parser.parse_args().port)
