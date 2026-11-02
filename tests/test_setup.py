"""Onboarding tests use temporary directories and fake credentials only."""
import argparse
from pathlib import Path

from dotenv import dotenv_values
import pytest

from scopus_mcp import config
from scopus_mcp.cli import setup
from scopus_mcp.cli.parser import build_parser
from scopus_mcp.exceptions import ScopusConfigError


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    path = tmp_path / "private" / "credentials.env"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "user_config_path", lambda: path)
    monkeypatch.setattr(setup, "user_config_path", lambda: path)
    monkeypatch.delenv("SCOPUS_API_KEY", raising=False)
    monkeypatch.delenv("SCOPUS_INST_TOKEN", raising=False)
    config.get_settings.cache_clear()
    yield path
    config.get_settings.cache_clear()


def options(*args):
    return build_parser().parse_args(["setup", *args])


def test_save_roundtrip_and_settings_precedence(isolated_config, monkeypatch, tmp_path):
    setup.save_credentials(isolated_config, "fake-user-key", "fake-token")
    assert config.get_settings().api_key == "fake-user-key"
    (tmp_path / ".env").write_text("SCOPUS_API_KEY=fake-project-key\n", encoding="utf-8")
    config.get_settings.cache_clear()
    assert config.get_settings().api_key == "fake-project-key"
    monkeypatch.setenv("SCOPUS_API_KEY", "fake-environment-key")
    config.get_settings.cache_clear()
    assert config.get_settings().api_key == "fake-environment-key"


def test_from_env_refuses_unrequested_overwrite(isolated_config, monkeypatch):
    monkeypatch.setenv("SCOPUS_API_KEY", "fake-original")
    assert setup.run_setup(options("--from-env"))["saved"]
    monkeypatch.setenv("SCOPUS_API_KEY", "fake-replacement")
    with pytest.raises(ValueError, match="--force"):
        setup.run_setup(options("--from-env"))
    assert dotenv_values(isolated_config)["SCOPUS_API_KEY"] == "fake-original"
    setup.run_setup(options("--from-env", "--force"))
    assert dotenv_values(isolated_config)["SCOPUS_API_KEY"] == "fake-replacement"


def test_status_never_contains_secrets(isolated_config):
    setup.save_credentials(isolated_config, "fake-private-key", "fake-private-token")
    result = setup.run_setup(options("--show"))
    assert result["configured"]
    assert "fake-private" not in str(result)


def test_explicit_setup_check_uses_saved_credentials(isolated_config, monkeypatch):
    setup.save_credentials(isolated_config, "fake-saved", None)
    monkeypatch.setenv("SCOPUS_API_KEY", "fake-external-override")
    monkeypatch.setenv("SCOPUS_INST_TOKEN", "fake-external-token")
    settings = setup.saved_settings()
    assert settings.api_key == "fake-saved"
    assert settings.inst_token is None


def test_optional_empty_token_is_unset(isolated_config, monkeypatch):
    monkeypatch.setenv("SCOPUS_API_KEY", "fake-key")
    monkeypatch.setenv("SCOPUS_INST_TOKEN", "")
    assert config.get_settings().inst_token is None


def test_secret_protection_failure_preserves_old_file(isolated_config, monkeypatch):
    setup.save_credentials(isolated_config, "fake-original", None)
    def fail(path):
        raise OSError("permissions unavailable")
    monkeypatch.setattr(setup, "_protect", fail)
    with pytest.raises(OSError):
        setup.save_credentials(isolated_config, "fake-replacement", None)
    assert dotenv_values(isolated_config)["SCOPUS_API_KEY"] == "fake-original"
    assert not list(isolated_config.parent.glob(".credentials-*"))


def test_piped_setup_never_prompts(isolated_config, monkeypatch):
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: False)
    with pytest.raises(ValueError, match="--from-env"):
        setup.run_setup(options())


def test_wizard_private_entry_and_cancel(isolated_config, monkeypatch, capsys):
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: True)
    inputs = iter(["fake-never-printed", ""])
    monkeypatch.setattr(setup, "_secret", lambda prompt: next(inputs))
    monkeypatch.setattr("builtins.input", lambda: "n")
    assert not setup.run_setup(options("--language", "es"))["saved"]
    assert not isolated_config.exists()
    assert "fake-never-printed" not in capsys.readouterr().err


def test_wizard_can_remove_saved_token(isolated_config, monkeypatch):
    setup.save_credentials(isolated_config, "fake-existing", "fake-token")
    monkeypatch.setattr(setup.sys.stdin, "isatty", lambda: True)
    inputs = iter(["", "-"])
    monkeypatch.setattr(setup, "_secret", lambda prompt: next(inputs))
    monkeypatch.setattr("builtins.input", lambda: "s")
    assert setup.run_setup(options("--language", "es"))["saved"]
    assert dotenv_values(isolated_config) == {"SCOPUS_API_KEY": "fake-existing"}


def test_invalid_settings_do_not_echo_credentials(isolated_config, monkeypatch):
    monkeypatch.setenv("SCOPUS_API_KEY", "private-fake-value")
    monkeypatch.setenv("SCOPUS_MAX_RETRIES", "bad-value")
    with pytest.raises(ScopusConfigError) as failure:
        config.get_settings()
    assert "private-fake-value" not in str(failure.value)
    assert "SCOPUS_MAX_RETRIES" in str(failure.value)


@pytest.mark.parametrize("key", ["", "\n", "fake\nINJECT=x", "fake\x00"])
def test_reject_unsafe_values(isolated_config, key):
    with pytest.raises(ValueError):
        setup.save_credentials(isolated_config, key, None)
    assert not isolated_config.exists()
