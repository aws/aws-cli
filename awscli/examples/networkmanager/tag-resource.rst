**To apply tags to a resource**

The following ``tag-resource`` example applies the tag ``Network=Northeast`` to the device ``device-07f6fd08867abc123``. ::

    aws networkmanager tag-resource \
        --resource-arn arn:aws:networkmanager::123456789012:device/global-network-01231231231231231/device-07f6fd08867abc123 \
        --tags Key=Network,Value=Northeast

This command produces no output.

For more information, see `Resource tags in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/gnw-tagging.html>`__ in the *AWS Global Networks for Transit Gateways User Guide*.
