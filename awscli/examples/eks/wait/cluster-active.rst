**To wait for an Amazon EKS cluster to become ACTIVE**

The following ``wait`` example command waits for an Amazon EKS cluster named ``my-eks-cluster`` to become active. 

    aws eks wait \
        cluster-active \
        --name my-eks-cluster

Output::

    <No Output>