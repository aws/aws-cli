**To describe Spot Instance datafeed subscription for an account**

This example command describes the data feed for the the account.

Command::

  aws ec2 describe-spot-datafeed-subscription

Output::

  {
      "SpotDatafeedSubscription": {
          "OwnerId": "<account-id>",
          "Prefix": "spotdata",
          "Bucket": "<s3-bucket-name>",
          "State": "Active"
      }
  }

