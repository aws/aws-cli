**To wait for a new code binding to be created from the put-code-binding API**

The following ``wait code-binding-exists`` example waits for a new code binding to be created from the put-code-binding API. ::

    aws schemas wait code-binding-exists \
        --registry-name example-registry \
        --schema-name example-schema \
        --schema-version 6 \
        --language Python36
        
This command produces no output.

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.