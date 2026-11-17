"""Train on pinned AWS CLI parsing, model loading and text formatting.

Only dependency-free upstream modules are imported: the complete driver
needs the _awscrt extension, which is built after CPython. No requests are
made, and no user configuration or credentials are read.
"""

import io
import json
import marshal
import sys
from pathlib import Path


def train(source: Path) -> None:
    sys.path.insert(0, str(source))
    from awscli.argparser import CLIArgParser, ServiceArgParser
    from awscli.text import format_text

    parser = CLIArgParser(prog="aws")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--output", choices=("json", "text", "table"))
    parser.add_argument("--query")
    parser.add_argument("--filters", nargs="+")
    parser.add_argument("--max-items", type=int)
    data_dir = source / "awscli" / "botocore" / "data"
    for service in ("s3", "ec2", "lambda", "dynamodb", "iam", "sts"):
        model_path = max((data_dir / service).glob("*/service-2.json"))
        model = json.loads(model_path.read_bytes())
        operations = model["operations"]
        service_parser = ServiceArgParser(operations, service)
        for operation in list(operations)[:12]:
            parsed, remaining = service_parser.parse_known_args([operation])
            assert parsed.operation == operation
            assert remaining == []
        for shape in model["shapes"].values():
            json.loads(json.dumps(shape))
    for relative in ("argparser.py", "text.py", "clidriver.py"):
        code = compile(
            (source / "awscli" / relative).read_bytes(),
            relative,
            "exec",
            optimize=2,
        )
        for _ in range(10):
            assert marshal.loads(marshal.dumps(code)).co_name == "<module>"
    response = {
        "Contents": [
            {
                "Key": f"prefix/object-{i}",
                "Size": i * 1024,
                "StorageClass": "STANDARD",
            }
            for i in range(50)
        ],
        "IsTruncated": False,
        "Name": "training-bucket",
    }
    encoded = json.dumps(response)
    for _ in range(100):
        args, rest = parser.parse_known_args(
            [
                "--output",
                "json",
                "--max-items",
                "50",
                "--query",
                "Contents[?Size > `0`].[Key,Size]",
                "--filters",
                "Name=tag:Name,Values=web-*",
            ]
        )
        assert args.max_items == 50
        assert rest == []
        decoded = json.loads(encoded)
        stream = io.StringIO()
        format_text(decoded, stream)
        assert "prefix/object-49" in stream.getvalue()
        output = io.StringIO()
        json.dump(decoded, output, indent=4, ensure_ascii=False)
        assert json.loads(output.getvalue()) == response


if __name__ == "__main__":
    train(Path(sys.argv[1]))
