**To delete the specified destination**

The following ``delete-destination`` example deletes the destination named ``demoDestination``, and disables all the subscription filters that publish to it. ::

    aws logs delete-destination \
        --destination-name demoDestination

This command produces no output.

For more information, see `Cross-account cross-Region subscriptions <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CrossAccountSubscriptions.html>`__ in the *Amazon CloudWatch Logs User Guide*.