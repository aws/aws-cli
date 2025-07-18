**To delete the schema version definition**

The following ``delete-schema-version`` example deletes the schema version definition. ::

    aws schemas delete-schema-version \
        --registry-name example-registry \
        --schema-name example-schema \
        --schema-version 2

This command produces no output.

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.