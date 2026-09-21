"""CLI de scorm-tools. Los comandos viven en los módulos cmd_*; importarlos los registra en `app`."""

from __future__ import annotations

from ._cli_base import SCHEMA_VERSION, __version__, _emit_json, app, console, err_console  # noqa: F401
from . import cmd_curso, cmd_chequeos, cmd_ecosistema  # noqa: F401
from .cmd_curso import _print_report  # noqa: F401


def main() -> None:
    app()


if __name__ == "__main__":
    main()
