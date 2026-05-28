"""JobPilot CLI — typer-based command-line interface.

This module owns the shared ``app``, ``console`` and helper functions. The
actual ``@app.command()`` implementations live in ``jobpilot.commands.*`` and
are registered by importing that package at the bottom of this file (the
register-at-bottom pattern avoids circular imports, since the command modules
import ``app``/``console``/helpers from here).
"""

from __future__ import annotations

import logging

import typer
from rich.console import Console

# ``config`` is re-exported here so command modules can reference
# ``cli.config.<X>`` and tests can patch ``jobpilot.cli.config``.
from jobpilot import __version__, config  # noqa: F401
from jobpilot.db import JobPilotDB

app = typer.Typer(
    name="jobpilot",
    help="JobPilot — AI-powered job hunting assistant",
    no_args_is_help=True,
)
console = Console()


def _get_db() -> JobPilotDB:
    return JobPilotDB()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


@app.command()
def version() -> None:
    """Show version."""
    console.print(f"JobPilot v{__version__}")


# Register all commands by importing the command modules. This MUST stay at the
# bottom, after app/console/helpers are defined, so the command modules can
# import them from here without a circular-import error.
from jobpilot.commands import (  # noqa: E402,F401  (register commands)
    advisor_cmds,
    apply_kit,
    discover,
    pipeline_cmds,
    quality,
)

# Re-export the shared scoring helper so callers (and test patches targeting
# ``jobpilot.cli._do_score``) resolve against this module.
_do_score = discover._do_score

if __name__ == "__main__":
    app()
