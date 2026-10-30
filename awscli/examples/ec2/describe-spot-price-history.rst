**Example 1: To describe Spot price history**

The following ``describe-spot-price-history`` example returns the Spot Price history for m1.xlarge instances for a particular day in January. ::

    aws ec2 describe-spot-price-history \
        --instance-types m1.xlarge \
        --start-time 2014-01-06T07:08:09 \
        --end-time 2014-01-06T08:09:10

Output::

    {
        "SpotPriceHistory": [
            {
                "Timestamp": "2014-01-06T07:10:55.000Z",
                "ProductDescription": "SUSE Linux",
                "InstanceType": "m1.xlarge",
                "SpotPrice": "0.087000",
                "AvailabilityZone": "us-west-2b"
            },
            {
                "Timestamp": "2014-01-06T07:10:55.000Z",
                "ProductDescription": "SUSE Linux",
                "InstanceType": "m1.xlarge",
                "SpotPrice": "0.087000",
                "AvailabilityZone": "us-west-2c"
            },
            {
                "Timestamp": "2014-01-06T05:42:36.000Z",
                "ProductDescription": "SUSE Linux (Amazon VPC)",
                "InstanceType": "m1.xlarge",
                "SpotPrice": "0.087000",
                "AvailabilityZone": "us-west-2a"
            }
        ]
    }

For more information, see `View Spot Instance pricing history <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances-history.html>`__ in the *Amazon EC2 User Guide*.

**Example 2: To describe Spot price history for Linux/UNIX Amazon VPC**

The following ``describe-spot-price-history`` example returns the Spot Price history for m1.xlarge, Linux/UNIX Amazon VPC instances for a particular day in January. ::

    aws ec2 describe-spot-price-history \
        --instance-types m1.xlarge \
        --product-description "Linux/UNIX (Amazon VPC)" \
        --start-time 2014-01-06T07:08:09 \
        --end-time 2014-01-06T08:09:10

Output::

    {
        "SpotPriceHistory": [
            {
                "Timestamp": "2014-01-06T04:32:53.000Z",
                "ProductDescription": "Linux/UNIX (Amazon VPC)",
                "InstanceType": "m1.xlarge",
                "SpotPrice": "0.080000",
                "AvailabilityZone": "us-west-2a"
            },
            {
                "Timestamp": "2014-01-05T11:28:26.000Z",
                "ProductDescription": "Linux/UNIX (Amazon VPC)",
                "InstanceType": "m1.xlarge",
                "SpotPrice": "0.080000",
                "AvailabilityZone": "us-west-2c"
            }
        ]
    }

For more information, see `View Spot Instance pricing history <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-spot-instances-history.html>`__ in the *Amazon EC2 User Guide*.
