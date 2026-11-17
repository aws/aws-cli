**To create an Amazon FPGA image**

The following ``create-fpga-image`` example creates an AFI from the specified tarball in the specified bucket. ::

    aws ec2 create-fpga-image \
        --name my-afi \
        --description test-afi \
        --input-storage-location Bucket=my-fpga-bucket,Key=dcp/17_12_22-103226.Developer_CL.tar \
        --logs-storage-location Bucket=my-fpga-bucket,Key=logs

Output::

    {
        "FpgaImageId": "afi-0d123e123bfc85abc",
        "FpgaImageGlobalId": "agfi-123cb27b5e84a0abc"
    }

For more information, see `Specifications for Amazon EC2 accelerated computing instances <https://docs.aws.amazon.com/ec2/latest/instancetypes/ac.html>`__ in the *Amazon EC2 Instance Types Guide*.
