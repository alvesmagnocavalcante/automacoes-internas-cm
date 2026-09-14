"""Ponto de entrada único para as automações do repositório."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from typing import TextIO

from automations.registry import AUTOMATIONS, get_automation


def print_help(*, file: TextIO | None = None) -> None:
    output = file or sys.stdout
    print("Uso: python main.py <automação> [argumentos]", file=output)
    print("\nAutomações disponíveis:", file=output)
    for slug, automation in sorted(AUTOMATIONS.items()):
        print(f"  {slug}: {automation.description}", file=output)


def main(argv: Sequence[str] | None = None) -> int:
    """Seleciona uma automação pelo nome e repassa seus argumentos."""
    arguments = list(argv if argv is not None else sys.argv[1:])

    if arguments == ["--list"]:
        print_help()
        return 0

    if arguments in (["-h"], ["--help"]):
        print_help()
        return 0

    if not arguments:
        print("Informe qual automação deve ser executada.\n", file=sys.stderr)
        print_help(file=sys.stderr)
        return 2

    slug = arguments.pop(0)

    try:
        automation = get_automation(slug)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    return automation.execute(arguments)


if __name__ == "__main__":
    sys.exit(main())
