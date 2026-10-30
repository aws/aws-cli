**To open a SOCKS connection to the primary node of a cluster**

The following ``socks`` example opens a socks connection with the master instance in a cluster with the cluster ID ``j-3SD91U2E1L2QX``. ::

    aws emr socks \
        --cluster-id j-3SD91U2E1L2QX \
        --key-pair-file ~/.ssh/mykey.pem

The key pair file option takes a local path to a private key file. The command displays the ``ssh`` command that it runs and keeps the tunnel open on local port 8157 until you press Ctrl+C.

Output::

    ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=10 -ND 8157 -i /home/local/user/.ssh/mykey.pem hadoop@ec2-52-52-41-150.us-west-2.compute.amazonaws.com
    Disabling Socks Tunnel.

For more information, see `Option 2, part 1: Set up an SSH tunnel to the primary node using dynamic port forwarding <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-ssh-tunnel.html>`__ in the *Amazon EMR Management Guide*.
