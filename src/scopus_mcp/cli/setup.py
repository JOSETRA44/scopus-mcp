"""Accessible terminal onboarding. No network or prompting during MCP startup."""
from __future__ import annotations

import getpass
import locale
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import warnings

from dotenv import dotenv_values

from ..config import ScopusSettings, get_settings, user_config_path
from ..exceptions import ScopusConfigError


def _protect(path: Path) -> None:
    if os.name == "nt":
        identity = subprocess.run(
            ["whoami", "/user", "/fo", "csv", "/nh"],
            capture_output=True, text=True, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        match = re.search(r"S-1-\d+(?:-\d+)+", identity.stdout)
        if not match:
            raise ScopusConfigError("Could not identify the Windows account; configuration was not saved.")
        subprocess.run(
            ["icacls", str(path), "/inheritance:r", "/grant:r", f"*{match.group()}:(F)"],
            capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        path.chmod(0o600)


def save_credentials(path: Path, api_key: str, inst_token: str | None) -> None:
    """Atomically replace only our credentials file; restrict it before writing."""
    values = {"SCOPUS_API_KEY": api_key.strip()}
    if inst_token and inst_token.strip():
        values["SCOPUS_INST_TOKEN"] = inst_token.strip()
    if not values["SCOPUS_API_KEY"] or any(
        any(c in value for c in ("\n", "\r", "\x00")) for value in values.values()
    ):
        raise ValueError("Credentials must be non-empty single-line values.")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=".credentials-", dir=path.parent)
    temporary = Path(name)
    os.close(descriptor)
    try:
        _protect(temporary)
        lines = ["# Created by scopus setup. Private local credentials; do not share."]
        for key, value in values.items():
            escaped = value.replace("\\", "\\\\").replace("'", "\\'")
            lines.append(f"{key}='{escaped}'")
        temporary.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    get_settings.cache_clear()


def _secret(prompt: str) -> str:
    # getpass normally falls back to echoing when no secure terminal exists.
    # Fail instead of accidentally showing a credential in a log.
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            return getpass.getpass(prompt).strip()
        except getpass.GetPassWarning as exc:
            raise ScopusConfigError("A private terminal is required. Use `scopus setup --from-env` for automation.") from exc
        except EOFError as exc:
            raise ValueError("Setup cancelled: no input was available.") from exc


def saved_settings() -> ScopusSettings:
    """An explicit setup check tests the saved credentials, not external overrides."""
    from pydantic import ValidationError
    values = dotenv_values(user_config_path(), interpolate=False)
    try:
        return ScopusSettings(_env_file=None,
                              SCOPUS_API_KEY=values.get("SCOPUS_API_KEY") or "",
                              SCOPUS_INST_TOKEN=values.get("SCOPUS_INST_TOKEN"))
    except ValidationError as exc:
        raise ScopusConfigError("Saved credentials or environment settings are invalid. Run scopus setup again.") from exc


def run_setup(args) -> dict:
    path = user_config_path()
    if args.show:
        existing = dotenv_values(path, interpolate=False) if path.exists() else {}
        return {"path": str(path), "configured": bool(existing.get("SCOPUS_API_KEY")),
                "institutional_token_configured": bool(existing.get("SCOPUS_INST_TOKEN")),
                "environment_override": bool(os.getenv("SCOPUS_API_KEY")),
                "project_override": bool(dotenv_values(Path.cwd() / ".env").get("SCOPUS_API_KEY"))}
    if args.from_env:
        if path.exists() and not args.force:
            raise ValueError("Configuration exists. Use --force to replace it, or run scopus setup interactively.")
        key = os.getenv("SCOPUS_API_KEY", "").strip()
        if not key:
            raise ScopusConfigError("Set SCOPUS_API_KEY before using --from-env.")
        token = os.getenv("SCOPUS_INST_TOKEN")
    else:
        if not sys.stdin.isatty():
            raise ValueError("Setup needs an interactive terminal. Use --from-env for automation, or --show to inspect configuration.")
        spanish = args.language == "es" or (
            args.language is None and (locale.getlocale()[0] or "").lower().startswith("es")
        )
        def say(en: str, es: str) -> None:
            print(es if spanish else en, file=sys.stderr)
        def ask(en: str, es: str) -> str:
            print(es if spanish else en, file=sys.stderr, end="", flush=True)
            try:
                return input().strip().lower()
            except EOFError as exc:
                raise ValueError("Setup cancelled: no input was available.") from exc
        say("Scopus setup — 3 steps. Press Ctrl+C to cancel.", "Configuración de Scopus — 3 pasos. Pulsa Ctrl+C para cancelar.")
        say("1. Get an API key: https://dev.elsevier.com/ . Access depends on Elsevier entitlements.",
            "1. Obtén una API key: https://dev.elsevier.com/ . El acceso depende de los permisos de Elsevier.")
        existing = dotenv_values(path, interpolate=False) if path.exists() else {}
        while True:
            label = "API key (hidden; Enter keeps saved key): " if existing.get("SCOPUS_API_KEY") else "API key (hidden): "
            label_es = "API key (oculta; Enter conserva la guardada): " if existing.get("SCOPUS_API_KEY") else "API key (oculta): "
            key = _secret(label_es if spanish else label) or existing.get("SCOPUS_API_KEY", "")
            if key:
                break
            say("An API key is required. Paste the key or press Ctrl+C to cancel.",
                "La API key es obligatoria. Pégala o pulsa Ctrl+C para cancelar.")
        say("2. Institutional token is optional. Enter keeps the saved token; '-' removes it.",
            "2. El token institucional es opcional. Enter conserva el guardado; '-' lo elimina.")
        entered = _secret("Token (oculto, opcional): " if spanish else "Token (hidden, optional): ")
        token = None if entered == "-" else entered or existing.get("SCOPUS_INST_TOKEN")
        say(f"3. Save to {path}\nCredentials are stored as local plaintext with restricted file permissions.",
            f"3. Guardar en {path}\nLas credenciales se guardan en texto plano local con permisos de archivo restringidos.")
        answer = ask("Save? [Y/n]: ", "¿Guardar? [S/n]: ")
        if answer not in ("", "y", "yes", "s", "si", "sí"):
            return {"saved": False, "path": str(path), "message": "Cancelled; configuration unchanged."}
    save_credentials(path, key, token)
    return {"saved": True, "path": str(path), "check_requested": bool(args.check),
            "environment_override": bool(os.getenv("SCOPUS_API_KEY")),
            "project_override": bool(dotenv_values(Path.cwd() / ".env").get("SCOPUS_API_KEY")),
            "next_step": "Run scopus check to test access. MCP clients can run uvx josetra-scopus-mcp without embedding the key.",
            "precedence": "Environment variables > working-directory .env > saved user configuration."}
