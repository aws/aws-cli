**To update a device**

The following ``update-device`` example updates device ``device-07f6fd08867abc123`` by specifying a site ID for the device. ::

    aws networkmanager update-device \
        --global-network-id global-network-01231231231231231 \
        --device-id device-07f6fd08867abc123 \
        --site-id site-444555aaabbb11223

Output::

    {
        "Device": {
            "DeviceId": "device-07f6fd08867abc123",
            "DeviceArn": "arn:aws:networkmanager::123456789012:device/global-network-01231231231231231/device-07f6fd08867abc123",
            "GlobalNetworkId": "global-network-01231231231231231",
            "Description": "NY office device",
            "Type": "Office device",
            "Vendor": "anycompany",
            "Model": "abcabc",
            "SerialNumber": "1234",
            "SiteId": "site-444555aaabbb11223",
            "CreatedAt": 1575554005.0,
            "State": "UPDATING"
        }
    }

For more information, see `Devices in AWS Global Networks for Transit Gateways <https://docs.aws.amazon.com/network-manager/latest/tgwnm/nm-devices.html>`__ in the *Transit Gateway Network Manager Guide*.
