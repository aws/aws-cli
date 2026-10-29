**Example 1: To list all the tags for an Amazon EKS Cluster ARN**

The following ``list-tags-for-resource`` example lists all the tags for an Amazon EKS Cluster ARN. ::

    aws eks list-tags-for-resource \
        --resource-arn arn:aws:eks:us-west-2:123456789012:cluster/my-eks-cluster

Output::

    {
        "tags": {
            "aws:cloudformation:stack-name": "eksctl-my-eks-cluster-cluster",
            "alpha.eksctl.io/cluster-name": "my-eks-cluster",
            "karpenter.sh/discovery": "my-eks-cluster",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:us-west-2:123456789012:stack/eksctl-my-eks-cluster-cluster/a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
            "auto-delete": "no",
            "eksctl.cluster.k8s.io/v1alpha1/cluster-name": "my-eks-cluster",
            "EKS-Cluster-Name": "my-eks-cluster",
            "alpha.eksctl.io/cluster-oidc-enabled": "true",
            "aws:cloudformation:logical-id": "ControlPlane",
            "alpha.eksctl.io/eksctl-version": "0.173.0-dev+a7ee89342.2024-03-01T03:40:57Z",
            "Name": "eksctl-my-eks-cluster-cluster/ControlPlane"
        }
    }

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To list all the tags for an Amazon EKS Node group ARN**

The following ``list-tags-for-resource`` example lists all the tags for an Amazon EKS Node group ARN. ::

    aws eks list-tags-for-resource \
        --resource-arn arn:aws:eks:us-west-2:123456789012:nodegroup/my-eks-cluster/my-eks-managed-node-group/a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "tags": {
            "aws:cloudformation:stack-name": "eksctl-my-eks-cluster-nodegroup-my-eks-managed-node-group",
            "aws:cloudformation:stack-id": "arn:aws:cloudformation:us-west-2:123456789012:stack/eksctl-my-eks-cluster-nodegroup-my-eks-managed-node-group/a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
            "eksctl.cluster.k8s.io/v1alpha1/cluster-name": "my-eks-cluster",
            "EKS-Cluster-Name": "my-eks-cluster",
            "alpha.eksctl.io/nodegroup-type": "managed",
            "NodeGroup Name 1": "my-eks-managed-node-group",
            "k8s.io/cluster-autoscaler/enabled": "true",
            "nodegroup-role": "worker",
            "alpha.eksctl.io/cluster-name": "my-eks-cluster",
            "alpha.eksctl.io/nodegroup-name": "my-eks-managed-node-group",
            "karpenter.sh/discovery": "my-eks-cluster",
            "NodeGroup Name 2": "AmazonLinux-Linux-Managed-NG-v1-26-v1",
            "auto-delete": "no",
            "k8s.io/cluster-autoscaler/my-eks-cluster": "owned",
            "aws:cloudformation:logical-id": "ManagedNodeGroup",
            "alpha.eksctl.io/eksctl-version": "0.173.0-dev+a7ee89342.2024-03-01T03:40:57Z"
        }
    }

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.

**Example 3: To list all the tags on an Amazon EKS Fargate profil ARNe**

The following ``list-tags-for-resource`` example lists all the tags for an Amazon EKS Fargate profile ARN. ::

    aws eks list-tags-for-resource  \
        --resource-arn arn:aws:eks:us-west-2:123456789012:fargateprofile/my-eks-cluster/my-fargate-profile/a1b2c3d4-5678-90ab-cdef-EXAMPLE44444

Output::

    {
        "tags": {
            "eks-fargate-profile-key-2": "value-2",
            "eks-fargate-profile-key-1": "value-1"
        }
    }

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.

**Example 4: To list all the tags for an Amazon EKS Add-on ARN**

The following ``list-tags-for-resource`` example lists all the tags for an Amazon EKS Add-on ARN. ::

    aws eks list-tags-for-resource \
        --resource-arn arn:aws:eks:us-west-2:123456789012:addon/my-eks-cluster/vpc-cni/a1b2c3d4-5678-90ab-cdef-EXAMPLE55555

Output::

    {
        "tags": {
            "eks-addon-key-2": "value-2",
            "eks-addon-key-1": "value-1"
        }
    }

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.

**Example 5: To list all the tags for an Amazon EKS OIDC identity provider ARN**

The following ``list-tags-for-resource`` example lists all the tags for an Amazon EKS OIDC identity provider ARN. ::

    aws eks list-tags-for-resource \
        --resource-arn arn:aws:eks:us-west-2:123456789012:identityproviderconfig/my-eks-cluster/oidc/my-identity-provider/a1b2c3d4-5678-90ab-cdef-EXAMPLE66666

Output::

    {
        "tags": {
            "my-identity-provider": "test"
        }
    }

For more information, see `Organize Amazon EKS resources with tags <https://docs.aws.amazon.com/eks/latest/userguide/eks-using-tags.html>`__ in the *Amazon EKS User Guide*.
