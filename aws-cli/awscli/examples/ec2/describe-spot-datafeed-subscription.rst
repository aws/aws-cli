**To describe Spot Instance datafeed subscription for an account**

The following ``describe-spot-datafeed-subscription`` example describes the data feed for the account. ::

    aws ec2 describe-spot-datafeed-subscription

Output::

    {
        "SpotDatafeedSubscription": {
            "OwnerId": "123456789012",
            "Prefix": "spotdata",
            "Bucket": "amzn-s3-demo-bucket",
            "State": "Active"
        }
    }

For more information, see `Track your Spot Instance costs using the Spot Instance data feed <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/spot-data-feeds.html>`__ in the *Amazon EC2 User Guide*.
