**To Delete the specified destination**

The following ``delete-destination`` example deletes the destination named ``demoDestination``, and eventually disables all the subscription filters that publish to it. If the command succeeds, no output is returned. ::

    aws logs delete-destination \
        --destination-name demoDestination

For more information, see `Cross-account cross-Region subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CrossAccountSubscriptions.html>`__ in the *Amazon CloudWatch Logs User Guide*.