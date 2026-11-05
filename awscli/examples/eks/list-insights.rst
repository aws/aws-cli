**To list all insights for the specified cluster**

The following ``list-insights`` example returns the list of all insights checked against the specified cluster. ::

    aws eks list-insights \
        --cluster-name eks-customer

Output::

    {
        "insights": [
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
                "name": "Kubelet version skew",
                "category": "UPGRADE_READINESS",
                "kubernetesVersion": "1.33",
                "lastRefreshTime": "2025-05-24T11:22:50-05:00",
                "lastTransitionTime": "2025-05-24T11:22:50-05:00",
                "description": "Checks for kubelet versions of worker nodes in the cluster to see if upgrade would cause noncompliance with supported Kubernetes kubelet version skew policy.",
                "insightStatus": {
                    "status": "PASSING",
                    "reason": "Node kubelet versions match the cluster control plane version."
                }
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
                "name": "EKS add-on version compatibility",
                "category": "UPGRADE_READINESS",
                "kubernetesVersion": "1.33",
                "lastRefreshTime": "2025-05-24T11:22:59-05:00",
                "lastTransitionTime": "2025-05-24T11:22:50-05:00",
                "description": "Checks version of installed EKS add-ons to ensure they are compatible with the next version of Kubernetes. ",
                "insightStatus": {
                    "status": "PASSING",
                    "reason": "All installed EKS add-on versions are compatible with next Kubernetes version."
                }
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE33333",
                "name": "Cluster health issues",
                "category": "UPGRADE_READINESS",
                "kubernetesVersion": "1.33",
                "lastRefreshTime": "2025-05-24T11:22:59-05:00",
                "lastTransitionTime": "2025-05-24T11:22:50-05:00",
                "description": "Checks for any cluster health issues that prevent successful upgrade to the next Kubernetes version on EKS.",
                "insightStatus": {
                    "status": "PASSING",
                    "reason": "No cluster health issues detected."
                }
            },
            {
                "id": "a1b2c3d4-5678-90ab-cdef-EXAMPLE44444",
                "name": "kube-proxy version skew",
                "category": "UPGRADE_READINESS",
                "kubernetesVersion": "1.33",
                "lastRefreshTime": "2025-05-24T11:22:50-05:00",
                "lastTransitionTime": "2025-05-24T11:22:50-05:00",
                "description": "Checks version of kube-proxy in cluster to see if upgrade would cause noncompliance with supported Kubernetes kube-proxy version skew policy.",
                "insightStatus": {
                    "status": "PASSING",
                    "reason": "kube-proxy versions match the cluster control plane version."
                }
            }
        ]
    }

For more information, see `View cluster insights <https://docs.aws.amazon.com/eks/latest/userguide/view-cluster-insights.html>`__ in the *Amazon EKS User Guide*.