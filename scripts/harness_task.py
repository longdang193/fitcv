from harness_core_launcher import run_core_cli


def main(argv: list[str] | None = None) -> int:
    return run_core_cli(argv)


if __name__ == "__main__":
    raise SystemExit(main())
