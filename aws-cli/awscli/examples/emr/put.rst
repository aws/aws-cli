**To upload a file to the primary node of a cluster**

The following ``put`` example uploads a file named ``healthcheck.sh`` to the master instance in a cluster with the cluster ID ``j-3SD91U2E1L2QX``. The command displays the ``scp`` command that it runs, followed by any output from ``scp``. ::

    aws emr put \
        --cluster-id j-3SD91U2E1L2QX \
        --key-pair-file ~/.ssh/mykey.pem \
        --src ~/scripts/healthcheck.sh \
        --dest /home/hadoop/bin/healthcheck.sh

Output::

    scp -r -o StrictHostKeyChecking=accept-new -i /home/local/user/.ssh/mykey.pem /home/local/user/scripts/healthcheck.sh hadoop@ec2-52-52-41-150.us-west-2.compute.amazonaws.com:/home/hadoop/bin/healthcheck.sh

For more information, see `Connect to an Amazon EMR cluster <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-connect-master-node.html>`__ in the *Amazon EMR Management Guide*.
