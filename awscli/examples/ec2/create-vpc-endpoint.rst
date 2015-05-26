**To create an endpoint**

This example creates a VPC endpoint between VPC vpc-1a2b3c4d and Amazon S3 in the us-east-1 region, and associates route table rtb-11aa22bb with the endpoint.

Command::

  aws ec2 create-vpc-endpoint --vpc-id vpc-1a2b3c4d --service-name com.amazonaws.us-east-1.s3 --route-table-ids rtb-11aa22bb

Output::

  {
    "VpcEndpoint": {
    "PolicyDocument": "{\"Version\":\"2008-10-17\",\"Statement\":[{\"Sid\":\"\",\"Effect\":\"Allow\",\"Principal\":\"*\",\"Action\":\"*\",\"Resource\":\"*\"}]}", 
    "VpcId": "vpc-1a2b3c4d", 
    "State": "available", 
    "ServiceName": "com.amazonaws.us-east-1.s3", 
    "RouteTableIds": [
      "rtb-11aa22bb"
    ], 
    "VpcEndpointId": "vpce-3ecf2a57", 
    "CreationTimestamp": "2015-05-15T09:40:50Z"
    }
  }