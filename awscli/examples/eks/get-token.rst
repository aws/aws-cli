**Example 1: To get an authentication token for an Amazon EKS Cluster named `my-eks-cluster`**

The following ``get-token`` example gets an authentication token for an Amazon EKS Cluster named `my-eks-cluster`. ::

    aws eks get-token \
        --cluster-name my-eks-cluster

Output::

    {
        "kind": "ExecCredential",
        "apiVersion": "client.authentication.k8s.io/v1beta1",
        "spec": {},
        "status": {
            "expirationTimestamp": "2024-04-11T20:59:56Z",
            "token": "k8s-aws-v1.EXAMPLE_TOKEN_DATA_STRING..."
        }
    }

For more information, see `Connect kubectl to an EKS cluster by creating a kubeconfig file <https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html>`__ in the *Amazon EKS User Guide*.

**Example 2: To get an authentication token for an Amazon EKS Cluster named `my-eks-cluster` by assuming a role ARN for credentials when signing the token**

The following ``get-token`` example gets an authentication token for an Amazon EKS Cluster named `my-eks-cluster` by assuming this roleARN for credentials when signing the token. ::

    aws eks get-token \
        --cluster-name my-eks-cluster \
        --role-arn arn:aws:iam::123456789012:role/eksctl-EKS-Linux-Cluster-v1-24-cluster-ServiceRole-j1k7AfTIQtnM

Output::

    {
        "kind": "ExecCredential",
        "apiVersion": "client.authentication.k8s.io/v1beta1",
        "spec": {},
        "status": {
            "expirationTimestamp": "2024-04-11T21:05:26Z",
            "token": "k8s-aws-v1.EXAMPLE_TOKEN_DATA_STRING..."
        }
    }

For more information, see `Connect kubectl to an EKS cluster by creating a kubeconfig file <https://docs.aws.amazon.com/eks/latest/userguide/create-kubeconfig.html>`__ in the *Amazon EKS User Guide*.
