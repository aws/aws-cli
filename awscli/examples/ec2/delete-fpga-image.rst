**To delete an Amazon FPGA image**

The following ``delete-fpga-image`` example deletes the specified AFI. ::

    aws ec2 delete-fpga-image \
        --fpga-image-id afi-06b12350a123fbabc

Output::

    {
        "Return": true
    }

For more information, see `Specifications for Amazon EC2 accelerated computing instances <https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html>`__ in the *Amazon EC2 Instance Types Guide*.
