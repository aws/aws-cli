**To wait for an Amazon EKS cluster to become deleted**

The following ``wait`` example command waits for an Amazon EKS cluster named ``my-eks-cluster`` to be deleted.

    aws eks wait \
        cluster-deleted \
        --name my-eks-cluster

Output::
  
    <No Output>
