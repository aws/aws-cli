def has_aws_command_any_kind():
    return {
        "has": {
            "kind": "command_name",
            "has": {
                "any": [
                    {
                        "kind": "word",
                        "pattern": "aws",
                    },
                    {
                        "kind": "string",
                        "pattern": '"aws"',
                    },
                    {"kind": "raw_string", "pattern": "'aws'"},
                ]
            },
        }
    }
