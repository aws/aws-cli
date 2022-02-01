**To delete an EC2 Fleet**

The following ``delete-fleets`` example deletes the specified EC2 Fleet and terminates the associated instances. ::

    aws ec2 delete-fleets \
        --fleet-ids fleet-12a34b55-67cd-8ef9-ba9b-9208dEXAMPLE \
        --terminate-instances

Output::

    {
        "SuccessfulFleetDeletions": [
            {
                "CurrentFleetState": "deleted_terminating",
                "PreviousFleetState": "active",
                "FleetId": "fleet-12a34b55-67cd-8ef9-ba9b-9208dEXAMPLE"
            }
        ],
        "UnsuccessfulFleetDeletions": []
    }

For more information, see `Managing an EC2 Fleet <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/manage-ec2-fleet.html>`__ in the *Amazon Elastic Compute Cloud User Guide for Linux Instances*.