**To describe endpoints**

This example describes all of your endpoints.

Command::

  aws ec2 describe-vpc-endpoints

Output::

  {
    "VpcEndpoints": [
      {
        "PolicyDocument": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"*\",\"Resource\":\"*\"}]}", 
        "VpcId": "vpc-ec43eb89", 
        "State": "available", 
        "ServiceName": "com.amazonaws.us-east-1.s3", 
        "RouteTableIds": [
          "rtb-4e5ef02b"
        ], 
        "VpcEndpointId": "vpce-3ecf2a57", 
        "CreationTimestamp": "2015-05-15T09:40:50Z"
      }
    ]
  } 