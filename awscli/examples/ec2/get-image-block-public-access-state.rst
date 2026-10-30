**To get the block public access state for AMIs in the current Region**

The following ``get-image-block-public-access-state`` example gets the block public access state for AMIs at the account level in the current Region. ::

    aws ec2 get-image-block-public-access-state

Output::

    {
        "ImageBlockPublicAccessState": "block-new-sharing"
    }

For more information, see `Block public access to your AMIs <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/block-public-access-to-amis.html>`__ in the *Amazon EC2 User Guide*.
