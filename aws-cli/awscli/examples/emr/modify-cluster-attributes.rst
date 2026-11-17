**To make a cluster visible to all users**

The following ``modify-cluster-attributes`` example sets the visibility of an EMR cluster with the ID ``j-301CDNY0J5XM4`` to all users. ::

    aws emr modify-cluster-attributes \
        --cluster-id j-301CDNY0J5XM4 \
        --visible-to-all-users

This command produces no output.

For more information, see `AWS Identity and Access Management for Amazon EMR <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-plan-access-iam.html>`__ in the *Amazon EMR Management Guide*.
