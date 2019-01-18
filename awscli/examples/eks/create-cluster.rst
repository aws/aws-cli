**To create a new cluster**

This example command creates a cluster named `prod` in your default region.

Command::

  aws eks create-cluster --name prod --role-arn arn:aws:iam::012345678910:role/eks-service-role-AWSServiceRoleForAmazonEKS-J7ONKE3BQ4PI --resources-vpc-config subnetIds=subnet-6782e71e,subnet-e7e761ac,securityGroupIds=sg-6979fe18

Output::

    {
        "cluster": {
            "name": "prod",
            "arn": "arn:aws:eks:us-west-2:012345678910:cluster/prod",
            "createdAt": 1527808069.147,
            "version": "1.10",
            "roleArn": "arn:aws:iam::012345678910:role/eks-service-role-AWSServiceRoleForAmazonEKS-J7ONKE3BQ4PI",
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
