**To describe an Elastic GPU**

The following ``describe-elastic-gpus`` example describes the specified Elastic GPU. ::

    aws ec2 describe-elastic-gpus \
        --elastic-gpu-ids egpu-12345678901234567890abcdefghijkl

Output::

    {
        "ElasticGpuSet": [
            {
                "ElasticGpuId": "egpu-12345678901234567890abcdefghijkl",
                "AvailabilityZone": "us-west-2a",
                "ElasticGpuType": "eg1.medium",
                "ElasticGpuHealth": {
                    "Status": "OK"
                },
                "ElasticGpuState": "ATTACHED",
                "InstanceId": "i-1234567890abcdef0"
            }
        ]
    }
