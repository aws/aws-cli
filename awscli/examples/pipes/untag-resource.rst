**To remove a Tag from an existing pipe**

The following ``untag-resource`` example removes a tag with the key ``stack`` from the Pipe named ``Demo_Pipe``. ::

    aws pipes untag-resource \
        --resource-arn arn:aws:pipes:us-west-2:123456789012:pipe/Demo_Pipe \
        --tag-keys stack

This command produces no output.

For more information, see `Amazon EventBridge Pipes concepts <https://docs.aws.amazon.com/eventbridge/latest/userguide/pipes-concepts.html>`__ in the *Amazon EventBridge User Guide*.