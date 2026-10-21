**To describe metadata model children**

The following ``describe-metadata-model-children`` example retrieves the child metadata models of the ``ExampleSchema`` schema from the source metadata tree. ::

    aws dms describe-metadata-model-children \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema"}, "rule-action": "explicit"}]}' \
        --origin SOURCE

Output::

    {
        "MetadataModelChildren": [
            {
                "MetadataModelName": "Tables",
                "SelectionRules": "{\"rules\": [{\"rule-type\": \"selection\", \"rule-id\": \"1\", \"rule-name\": \"1\", \"object-locator\": {\"server-name\": \"example-source-server.us-east-1.rds.amazonaws.com\", \"schema-name\": \"ExampleSchema\", \"category-name\": \"Tables\"}, \"rule-action\": \"explicit\"}]}"
            },
            {
                "MetadataModelName": "Views",
                "SelectionRules": "{\"rules\": [{\"rule-type\": \"selection\", \"rule-id\": \"2\", \"rule-name\": \"2\", \"object-locator\": {\"server-name\": \"example-source-server.us-east-1.rds.amazonaws.com\", \"schema-name\": \"ExampleSchema\", \"category-name\": \"Views\"}, \"rule-action\": \"explicit\"}]}"
            },
            {
                "MetadataModelName": "Functions",
                "SelectionRules": "{\"rules\": [{\"rule-type\": \"selection\", \"rule-id\": \"3\", \"rule-name\": \"3\", \"object-locator\": {\"server-name\": \"example-source-server.us-east-1.rds.amazonaws.com\", \"schema-name\": \"ExampleSchema\", \"category-name\": \"Functions\"}, \"rule-action\": \"explicit\"}]}"
            },
            {
                "MetadataModelName": "Sequences",
                "SelectionRules": "{\"rules\": [{\"rule-type\": \"selection\", \"rule-id\": \"4\", \"rule-name\": \"4\", \"object-locator\": {\"server-name\": \"example-source-server.us-east-1.rds.amazonaws.com\", \"schema-name\": \"ExampleSchema\", \"category-name\": \"Sequences\"}, \"rule-action\": \"explicit\"}]}"
            }
        ]
    }

For more information, see `Navigating the metadata model tree <https://docs.aws.amazon.com/dms/latest/userguide/sc-metadata-model.html#sc-metadata-model-navigating>`__ in the *AWS Database Migration Service User Guide*.
