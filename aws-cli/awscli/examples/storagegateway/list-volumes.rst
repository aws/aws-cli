**To list the volumes configured for a gateway**

The following ``list-volumes`` example returns a list of volumes configured for the specified gateway.
To specify which gateway to describe, use the Amazon Resource Name (ARN) of the gateway in the command.

This example specifies a gateway with the id ``sgw-12A3456B`` in account ``123456789012``. ::

    aws storagegateway list-volumes \
        --gateway-arn "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B"

This command outputs a JSON block that a list of volumes that includes the type and ARN for each volume.

Output::

    {
        "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B",
        "VolumeInfos": [
            {
                "VolumeARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B/volume/vol-1122AABB",
                "VolumeId": "vol-1122AABB",
                "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B",
                "GatewayId": "sgw-12A3456B",
                "VolumeType": "STORED",
                "VolumeSizeInBytes": 10737418240,
                "VolumeAttachmentStatus": "ATTACHED"
            },
            {
                "VolumeARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B/volume/vol-3344CCDD",
                "VolumeId": "vol-3344CCDD",
                "GatewayARN": "arn:aws:storagegateway:us-west-2:123456789012:gateway/sgw-12A3456B",
                "GatewayId": "sgw-12A3456B",
                "VolumeType": "STORED",
                "VolumeSizeInBytes": 10737418240,
                "VolumeAttachmentStatus": "ATTACHED"
            }
        ]
    }

For more information, see `Managing Your Volume Gateway <https://docs.aws.amazon.com/storagegateway/latest/vgw/managing-gateway-common.html>`__ in the *AWS Storage Gateway Volume Gateway User Guide*.
