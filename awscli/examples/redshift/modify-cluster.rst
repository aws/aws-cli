**Example 1: To associate a security group with a cluster**

The following ``modify-cluster`` example associates a cluster security group with the specified cluster. ::

    aws redshift modify-cluster --cluster-identifier mycluster --cluster-security-groups mysecuritygroup


**Example 2: To modify the maintenance window for a cluster**

The following ``modify-cluster`` example changes the weekly preferred maintenance window for a cluster to be the minimum four hour window
starting Sundays at 11:15 PM, and ending Mondays at 3:15 AM. ::

    aws redshift modify-cluster --cluster-identifier mycluster --preferred-maintenance-window Sun:23:15-Mon:03:15

**Example 3: To change the master password for the cluster**

The following ``modify-cluster`` example changes the master password for a cluster. ::

    aws redshift modify-cluster --cluster-identifier mycluster --master-user-password A1b2c3d4


