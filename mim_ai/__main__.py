from __future__ import annotations

import argparse

from .config import write_default_config


def init_main() -> int:
    parser = argparse.ArgumentParser(description="Create a MIM config file.")
    parser.add_argument(
        "path", nargs="?", default="mim_config.yaml", help="Target config path"
    )
    args = parser.parse_args()
    created = write_default_config(args.path, overwrite=False)
    print(f"Config ready at {created}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="MIM CLI")
    parser.add_argument(
        "command",
        choices=["init"],
        nargs="?",
        help="Create a default config file for a project.",
    )
    parser.add_argument(
        "path", nargs="?", default="mim_config.yaml", help="Target config path"
    )
    args = parser.parse_args()

    if args.command == "init":
        created = write_default_config(args.path, overwrite=False)
        print(f"Created default config at {created}")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
