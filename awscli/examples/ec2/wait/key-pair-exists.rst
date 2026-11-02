**To wait until a key pair exists**

The following ``wait key-pair-exists`` example pauses and resumes running only after it confirms that the specified key pair exists. ::

    aws ec2 wait key-pair-exists \
        --key-names my-key-pair

This command produces no output.

For more information, see `Amazon EC2 key pairs and Amazon EC2 instances <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-key-pairs.html>`__ in the *Amazon EC2 User Guide*.
