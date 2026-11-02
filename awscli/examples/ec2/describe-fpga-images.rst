**To describe Amazon FPGA images**

The following ``describe-fpga-images`` example describes AFIs that are owned by account ``123456789012``. ::

    aws ec2 describe-fpga-images \
        --filters Name=owner-id,Values=123456789012

Output::

    {
        "FpgaImages": [
            {
                "UpdateTime": "2017-12-22T12:09:14.000Z",
                "Name": "my-afi",
                "PciId": {
                    "SubsystemVendorId": "0xfedd",
                    "VendorId": "0x1d0f",
                    "DeviceId": "0xf000",
                    "SubsystemId": "0x1d51"
                },
                "FpgaImageGlobalId": "agfi-123cb27b5e84a0abc",
                "Public": false,
                "State": {
                    "Code": "available"
                },
                "ShellVersion": "0x071417d3",
                "OwnerId": "123456789012",
                "FpgaImageId": "afi-0d123e123bfc85abc",
                "CreateTime": "2017-12-22T11:43:33.000Z",
                "Description": "my-afi"
            }
        ]
    }

For more information, see `Specifications for Amazon EC2 accelerated computing instances <https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html>`__ in the *Amazon EC2 Instance Types Guide*.
