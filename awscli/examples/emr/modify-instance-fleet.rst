**To change the target capacites of an instance fleet**

The following ``modify-instance-fleet`` example changes the On-Demand and Spot target capacities to 1 for the specified instance fleet. ::

    aws emr modify-instance-fleet \
        --cluster-id 'j-12ABCDEFGHI34JK' \
        --instance-fleet InstanceFleetId='if-2ABC4DEFGHIJ4',TargetOnDemandCapacity=1,TargetSpotCapacity=1
