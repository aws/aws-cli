**To convert source selection rules to target selection rules**

The following ``get-target-selection-rules`` example converts source selection rules that select the ``ExampleTable`` table in the ``ExampleSchema`` schema into target selection rules that reference its converted counterpart. ::

    aws dms get-target-selection-rules \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "database-name": "ExampleDatabase", "schema-name": "ExampleSchema", "table-name": "ExampleTable"}, "rule-action": "explicit"}]}'

Output::

    {
        "TargetSelectionRules": "{\"rules\": [{\"rule-type\": \"selection\", \"rule-id\": \"1\", \"rule-name\": \"1\", \"object-locator\": {\"server-name\": \"example-target-server.us-east-1.rds.amazonaws.com\", \"schema-name\": \"exampledatabase_exampleschema\", \"table-name\": \"exampletable\"}, \"rule-action\": \"explicit\"}]}"
    }

For more information, see `Using selection rules <https://docs.aws.amazon.com/dms/latest/userguide/sc-selection-rules.html>`__ in the *AWS Database Migration Service User Guide*.
