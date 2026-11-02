**To remove tags from a resource**

The following ``untag-resource`` example removes the tag with the key ``Network`` from the device ``device-07f6fd08867abc123``. ::

    aws networkmanager untag-resource \
        --resource-arn arn:aws:networkmanager::123456789012:device/global-network-01231231231231231/device-07f6fd08867abc123 \
        --tag-keys Network

This command produces no output.

For more information, see `Resource tags in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/gnw-tagging.html>`__ in the *AWS Global Networks for Transit Gateways User Guide*.
