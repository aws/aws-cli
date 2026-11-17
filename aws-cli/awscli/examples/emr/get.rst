**To download a file from the primary node of a cluster**

The following ``get`` example downloads the ``hadoop-examples.jar`` archive from the master instance in a cluster with the cluster ID ``j-3SD91U2E1L2QX``. The command displays the ``scp`` command that it runs, followed by any output from ``scp``. ::

    aws emr get \
        --cluster-id j-3SD91U2E1L2QX \
        --key-pair-file ~/.ssh/mykey.pem \
        --src /home/hadoop-examples.jar \
        --dest ~

Output::

    scp -r -o StrictHostKeyChecking=accept-new -i /home/local/user/.ssh/mykey.pem hadoop@ec2-52-52-41-150.us-west-2.compute.amazonaws.com:/home/hadoop-examples.jar /home/local/user

For more information, see `Connect to the Amazon EMR cluster primary node using SSH <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-connect-master-node-ssh.html>`__ in the *Amazon EMR Management Guide*.
