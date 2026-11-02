**To wait until the password data for a Windows instance is available**

The following ``wait password-data-available`` example pauses and resumes running only after it confirms that the password data for the specified Windows instance is available. ::

    aws ec2 wait password-data-available \
        --instance-id i-1234567890abcdef0

This command produces no output.

For more information, see `Connect to your Windows instance using an RDP client <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect-rdp.html>`__ in the *Amazon EC2 User Guide*.
