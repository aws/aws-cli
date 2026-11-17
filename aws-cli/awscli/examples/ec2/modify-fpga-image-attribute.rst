**To modify the attributes of an Amazon FPGA image**

The following ``modify-fpga-image-attribute`` example adds load permissions for account ID ``123456789012`` for the specified AFI. ::

    aws ec2 modify-fpga-image-attribute \
        --attribute loadPermission \
        --fpga-image-id afi-0d123e123bfc85abc \
        --load-permission Add=[{UserId=123456789012}]

Output::

    {
        "FpgaImageAttribute": {
            "FpgaImageId": "afi-0d123e123bfc85abc",
            "LoadPermissions": [
                {
                    "UserId": "123456789012"
                }
            ]
        }
    }

For more information, see `Specifications for Amazon EC2 accelerated computing instances <https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html>`__ in the *Amazon EC2 Instance Types Guide*.
