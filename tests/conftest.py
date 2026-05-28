"""Shared pytest fixtures.

Test isolation: since config now auto-loads .env, a real ANTHROPIC_API_KEY /
SMTP credentials could leak into tests and trigger real network calls (slow,
costs money, rate limits). Force them empty for every test. Tests that exercise
the API path patch `config` locally, which overrides this.
"""

import pytest

from jobpilot import config


@pytest.fixture(autouse=True)
def _no_real_credentials(monkeypatch):
    monkeypatch.setattr(config, "ANTHROPIC_API_KEY", "", raising=False)
    monkeypatch.setattr(config, "SMTP_USER", "", raising=False)
    monkeypatch.setattr(config, "SMTP_PASSWORD", "", raising=False)
