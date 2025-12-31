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
                        "has": {"kind": "string_content", "nthChild": 1, "regex": "\\Aaws\\z"},
                    },
                    {"kind": "raw_string", "regex": "aws"},
                ]
            },
        }
    }
