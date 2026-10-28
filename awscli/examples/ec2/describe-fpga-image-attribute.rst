**To describe the attributes of an Amazon FPGA image**

The following ``describe-fpga-image-attribute`` example describes the load permissions for the specified AFI. ::

    aws ec2 describe-fpga-image-attribute \
        --fpga-image-id afi-0d123e123bfc85abc \
        --attribute loadPermission

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
