"""Compile the parser oracle bootstrap with the binary's own interpreter.

Only the noninstalled capture executable embeds this output. The installed
CLI always embeds the unmodified runtime bootstrap from the payload producer.
"""

import marshal
import sys
from pathlib import Path


def main() -> None:
    runtime, capture, output = map(Path, sys.argv[1:])
    source = runtime.read_text(encoding="utf-8")
    handoff = "sys.exit(_clidriver.main())\n"
    if not source.endswith(handoff):
        raise ValueError("runtime bootstrap must end with CLIDriver dispatch")
    source = source.removesuffix(handoff)
    source += capture.read_text(encoding="utf-8")
    source += (
        "\ncapture_parse_requests(sys.argv[1], _ZIPPY_AWSCLI_DATA)\n"
        "sys.exit(0)\n"
    )
    output.write_bytes(
        marshal.dumps(
            compile(
                source,
                "<parse-capture>",
                "exec",
                dont_inherit=True,
                optimize=2,
            )
        )
    )


if __name__ == "__main__":
    main()
