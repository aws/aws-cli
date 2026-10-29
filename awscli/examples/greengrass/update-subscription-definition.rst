**To update the name for a subscription definition**

The following ``update-subscription-definition`` example updates the name for the specified subscription definition. If you want to change details for the subscription, use the ``create-subscription-definition-version`` command to create a new version. ::

    aws greengrass update-subscription-definition \
        --subscription-definition-id "fa81bc84-3f59-4377-a84b-5d0134da359b" \
        --name "ObsoleteSubscription"

This command produces no output.

For more information, see `Overview of the AWS IoT Greengrass group object model <https://docs.aws.amazon.com/greengrass/v1/developerguide/deployments.html#api-overview>`__ in the *AWS IoT Greengrass Version 1 Developer Guide*.
