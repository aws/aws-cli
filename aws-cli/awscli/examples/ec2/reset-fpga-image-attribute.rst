**To reset the attributes of an Amazon FPGA image**

The following ``reset-fpga-image-attribute`` example resets the load permissions for the specified AFI. ::

    aws ec2 reset-fpga-image-attribute \
        --fpga-image-id afi-0d123e123bfc85abc \
        --attribute loadPermission

Output::

    {
        "Return": true
    }

For more information, see `Specifications for Amazon EC2 accelerated computing instances <https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html>`__ in the *Amazon EC2 Instance Types Guide*.
