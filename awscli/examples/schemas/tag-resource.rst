**To add tags to either a schema or registry**

The following ``tag-resource`` example adds tags to either a schema or registry. ::

    aws schemas tag-resource \
        --resource-arn arn:aws:schemas:region:account:registry/example-registry \
        --tags "{\"Environment\": \"Development\", \"App\": \"PetShop\"}"
        
This command produces no output.

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.