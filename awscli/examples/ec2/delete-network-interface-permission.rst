**To delete a network interface permission**

The following ``delete-network-interface-permission`` example deletes the specified network interface permission. ::

    aws ec2 delete-network-interface-permission \
        --network-interface-permission-id eni-perm-06fd19020ede149ea

Output::

    {
        "Return": true
    }

For more information, see `Elastic network interfaces <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html>`__ in the *Amazon EC2 User Guide*.
