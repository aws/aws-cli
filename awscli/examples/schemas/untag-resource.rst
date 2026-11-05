**To remove tags to either a schema or registry**

The following ``untag-resource`` example removes tags to either a schema or registry. You may specify the tag keys to remove. ::

    aws schemas untag-resource \
        --resource-arn arn:aws:schemas:region:account:registry/example-registry \
        --tag-keys Environment App
        
This command produces no output.

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.