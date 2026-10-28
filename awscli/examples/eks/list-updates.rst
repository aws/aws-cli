**Example 1: To list the updates for a cluster**

The following ``list-updates`` example lists the current updates for a cluster named ``example`` in your default region. ::

    aws eks list-updates --name example

Output::

    {
        "updateIds": [
            "10bddb13-a71b-425a-b0a6-71cd03e59161"
        ]
    }

**Example 2: To list all the update IDs for an Amazon EKS Node group**

The following ``list-updates`` example lists all the update IDs for an Amazon EKS Node group. ::

    aws eks list-updates \
        --name my-eks-cluster \
        --nodegroup-name my-eks-managed-node-group

Output::

    {
        "updateIds": [
            "8c6c1bef-61fe-42ac-a242-89412387b8e7"
        ]
    }

**Example 3: To list all the update IDs for an Amazon EKS add-on**

The following ``list-updates`` example lists all the update IDs for an Amazon EKS Add-on. ::

    aws eks list-updates \
        --name my-eks-cluster \
        --addon-name vpc-cni

Output::

    {
        "updateIds": [
            "9cdba8d4-79fb-3c83-afe8-00b508d33268"
        ]
    }
