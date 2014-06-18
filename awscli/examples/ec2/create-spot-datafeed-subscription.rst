**To create a Spot Instance datafeed**

This example command creates a Spot Instance data feed for the account.

Command::

  aws ec2 create-spot-datafeed-subscription --bucket <s3-bucket-name> --prefix spotdata

Output::

  {
      "SpotDatafeedSubscription": {
          "OwnerId": "<account-id>",
          "Prefix": "spotdata",
          "Bucket": "<s3-bucket-name>",
          "State": "Active"
      }
  }

