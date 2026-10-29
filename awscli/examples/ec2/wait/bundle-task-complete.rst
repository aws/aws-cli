**To pause running until a bundle task is completed**

The following ``wait bundle-task-complete`` example pauses and continues only after it can confirm that the specified bundle task is completed. ::

    aws ec2 wait bundle-task-complete \
        --bundle-ids bun-2a4e041c

This command produces no output.