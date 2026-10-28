**To delete a route**

The following ``delete-route`` example deletes the specified route from the specified route table. This command produces no output. ::

    aws ec2 delete-route \
        --route-table-id rtb-22574640 \
        --destination-cidr-block 0.0.0.0/0
