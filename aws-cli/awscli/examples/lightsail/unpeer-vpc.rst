**To unpeer the Amazon Lightsail virtual private cloud**

The following ``unpeer-vpc`` example unpeers the Amazon Lightsail virtual private cloud (VPC) for the current AWS Region. ::

    aws lightsail unpeer-vpc

Output::

    {
        "operation": {
            "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "resourceName": "vpc-0EXAMPLEa5261efb3",
            "resourceType": "PeeredVpc",
            "createdAt": 1571694109.945,
            "location": {
                "availabilityZone": "all",
                "regionName": "us-west-2"
            },
            "isTerminal": true,
            "operationDetails": "vpc-e2b3eb9b",
            "operationType": "UnpeeredVpc",
            "status": "Succeeded",
            "statusChangedAt": 1571694109.945
        }
    }

For more information, see `Connect Lightsail resources to AWS services using VPC peering <https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-set-up-vpc-peering-with-aws-resources.html>`__ in the *Amazon Lightsail User Guide*.
