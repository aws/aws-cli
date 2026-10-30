**To delete a subscription definition**

The following ``delete-subscription-definition`` example  deletes the specified Greengrass subscription definition. If you delete a subscription that is being used by a group, that group can't be deployed successfully. ::

    aws greengrass delete-subscription-definition \
        --subscription-definition-id "cd6f1c37-d9a4-4e90-be94-01a7404f5967"

This command produces no output.

For more information, see `Configure subscriptions <https://docs.aws.amazon.com/greengrass/v1/developerguide/config_subs.html>`__ in the *AWS IoT Greengrass Developer Guide*.
