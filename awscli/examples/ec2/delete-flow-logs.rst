**To delete a flow log**

The following ``delete-flow-logs`` example deletes the specified flow log. ::

    aws ec2 delete-flow-logs \
        --flow-log-id fl-11223344556677889

Output::

    {
        "Unsuccessful": []
    }

For more information, see `Work with flow logs <https://docs.aws.amazon.com/vpc/latest/userguide/working-with-flow-logs.html>`__ in the *Amazon VPC User Guide*.
