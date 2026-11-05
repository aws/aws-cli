**To Tag an existing pipe**

The following ``tag-resource`` example tags a Pipe named ``Demo_Pipe``. ::

    aws pipes tag-resource \
        --resource-arn arn:aws:pipes:us-west-2:123456789012:pipe/Demo_Pipe \
        --tags stack=Production

This command produces no output.

For more information, see `Amazon EventBridge Pipes concepts <https://docs.aws.amazon.com/eventbridge/latest/userguide/pipes-concepts.html>`__ in the *Amazon EventBridge User Guide*.