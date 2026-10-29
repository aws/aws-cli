**To add a task instance fleet to a cluster**

The following ``add-instance-fleet`` example adds a new task instance fleet to the cluster specified. ::

    aws emr add-instance-fleet \
        --cluster-id 'j-12ABCDEFGHI34JK' \
        --instance-fleet InstanceFleetType=TASK,TargetSpotCapacity=1,LaunchSpecifications={SpotSpecification='{TimeoutDurationMinutes=20,TimeoutAction=TERMINATE_CLUSTER}'},InstanceTypeConfigs=['{InstanceType=m3.xlarge,BidPrice=0.5}']

Output::

    {
        "ClusterId": "j-12ABCDEFGHI34JK",
        "InstanceFleetId": "if-23ABCDEFGHI45JJ"
    }

For more information, see `Planning and configuring instance fleets for your Amazon EMR cluster <https://docs.aws.amazon.com/emr/latest/ManagementGuide/emr-instance-fleet.html>`__ in the *Amazon EMR Management Guide*.
