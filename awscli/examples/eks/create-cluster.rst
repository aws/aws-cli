**Example 1: To create a new cluster**

The following ``create-cluster`` example creates a cluster named ``prod`` in your default region. ::

    aws eks create-cluster \
        --name prod \
        --role-arn arn:aws:iam::123456789012:role/eks-service-role-AWSServiceRoleForAmazonEKS-J7ONKE3BQ4PI \
        --resources-vpc-config subnetIds=subnet-6782e71e,subnet-e7e761ac,securityGroupIds=sg-6979fe18

Output::

    {
        "cluster": {
            "name": "prod",
            "arn": "arn:aws:eks:us-west-2:123456789012:cluster/prod",
            "createdAt": 1527808069.147,
            "version": "1.10",
            "roleArn": "arn:aws:iam::123456789012:role/eks-service-role-AWSServiceRoleForAmazonEKS-J7ONKE3BQ4PI",
            "resourcesVpcConfig": {
                "subnetIds": [
                    "subnet-6782e71e",
                    "subnet-e7e761ac"
                ],
                "securityGroupIds": [
                    "sg-6979fe18"
                ],
                "vpcId": "vpc-950809ec"
            },
            "status": "CREATING",
            "certificateAuthority": {}
        }
    }

For more information, see `Create an Amazon EKS cluster <https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To create a new cluster with private endpoint access and logging enabled**

The following ``create-cluster`` example creates a cluster named ``example`` in your default region with public endpoint access disabled, private endpoint access enabled, and all logging types enabled. ::

    aws eks create-cluster \
        --name example \
        --kubernetes-version 1.12 \
        --role-arn arn:aws:iam::123456789012:role/example-cluster-ServiceRole-1XWBQWYSFRE2Q \
        --resources-vpc-config subnetIds=subnet-0a188dccd2f9a632f,subnet-09290d93da4278664,subnet-0f21dd86e0e91134a,subnet-0173dead68481a583,subnet-051f70a57ed6fcab6,subnet-01322339c5c7de9b4,securityGroupIds=sg-0c5b580845a031c10,endpointPublicAccess=false,endpointPrivateAccess=true \
        --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'

Output::

    {
        "cluster": {
            "name": "example",
            "arn": "arn:aws:eks:us-west-2:123456789012:cluster/example",
            "createdAt": 1565804921.901,
            "version": "1.12",
            "roleArn": "arn:aws:iam::123456789012:role/example-cluster-ServiceRole-1XWBQWYSFRE2Q",
            "resourcesVpcConfig": {
                "subnetIds": [
                    "subnet-0a188dccd2f9a632f",
                    "subnet-09290d93da4278664",
                    "subnet-0f21dd86e0e91134a",
                    "subnet-0173dead68481a583",
                    "subnet-051f70a57ed6fcab6",
                    "subnet-01322339c5c7de9b4"
                ],
                "securityGroupIds": [
                    "sg-0c5b580845a031c10"
                ],
                "vpcId": "vpc-0f622c01f68d4afec",
                "endpointPublicAccess": false,
                "endpointPrivateAccess": true
            },
            "logging": {
                "clusterLogging": [
                    {
                        "types": [
                            "api",
                            "audit",
                            "authenticator",
                            "controllerManager",
                            "scheduler"
                        ],
                        "enabled": true
                    }
                ]
            },
            "status": "CREATING",
            "certificateAuthority": {},
            "platformVersion": "eks.3"
        }
    }

For more information, see `Create an Amazon EKS cluster <https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html>`__ in the *Amazon EKS User Guide*.
