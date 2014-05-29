**To describe Reserved Instances offerings**

This example command describes all Reserved Instances available for purchase in the region.

Command::

  aws ec2 describe-reserved-instances-offerings 
  
Output::

{
    "ReservedInstancesOfferings": [
        {
            "OfferingType": "Heavy Utilization", 
            "FixedPrice": 631.0, 
            "InstanceTenancy": "default", 
            "PricingDetails": [], 
            "ProductDescription": "Red Hat Enterprise Linux", 
            "UsagePrice": 0.0, 
            "RecurringCharges": [
                {
                    "Amount": 0.104, 
                    "Frequency": "Hourly"
                }
            ], 
            "Marketplace": false, 
            "CurrencyCode": "USD", 
            "AvailabilityZone": "us-west-1a", 
            "Duration": 94608000, 
            "ReservedInstancesOfferingId": "9a06095a-bdc6-47fe-a94a-2a382f016040", 
            "InstanceType": "c1.medium"
        }, 
        {
            "OfferingType": "Heavy Utilization", 
            "FixedPrice": 631.0, 
            "InstanceTenancy": "default", 
            "PricingDetails": [], 
            "ProductDescription": "Linux/UNIX", 
            "UsagePrice": 0.0, 
            "RecurringCharges": [
                {
                    "Amount": 0.044, 
                    "Frequency": "Hourly"
                }
            ], 
            "Marketplace": false, 
            "CurrencyCode": "USD", 
            "AvailabilityZone": "us-west-1a", 
            "Duration": 94608000, 
            "ReservedInstancesOfferingId": "bfbefc6c-0d10-418d-b144-7258578d329d", 
            "InstanceType": "c1.medium"
        }, 
        ...
        }
  }        

**To describe your Reserved Instances offerings using filters**

This example filters the list of Reserved Instances offerings to include only AWS offerings of m1.small, Linux/UNIX Reserved Instances in us-west-1c.

Command::

  aws ec2 describe-reserved-instances-offerings --no-include-marketplace --filters Name=instance-type,Values=m1.small, Name=product-description,Values=Linux/UNIX, Name=availability-zone,Values=us-west-1c

Output::

{
    "ReservedInstancesOfferings": [
        {
            "OfferingType": "Heavy Utilization", 
            "FixedPrice": 188.0, 
            "InstanceTenancy": "default", 
            "PricingDetails": [], 
            "ProductDescription": "Linux/UNIX", 
            "UsagePrice": 0.0, 
            "RecurringCharges": [
                {
                    "Amount": 0.013, 
                    "Frequency": "Hourly"
                }
            ], 
            "Marketplace": false, 
            "CurrencyCode": "USD", 
            "AvailabilityZone": "us-west-1c", 
            "Duration": 94608000, 
            "ReservedInstancesOfferingId": "5ca9ed27-054f-45f6-99db-cb55f1ffbdd4", 
            "InstanceType": "m1.small"
        }, 
        {
            "OfferingType": "Medium Utilization", 
            "FixedPrice": 157.0, 
            "InstanceTenancy": "default", 
            "PricingDetails": [], 
            "ProductDescription": "Linux/UNIX", 
            "UsagePrice": 0.016, 
            "RecurringCharges": [], 
            "Marketplace": false, 
            "CurrencyCode": "USD", 
            "AvailabilityZone": "us-west-1c", 
            "Duration": 94608000, 
            "ReservedInstancesOfferingId": "ec06327e-dd07-46ee-9398-75b5fe535820", 
            "InstanceType": "m1.small"
        },...
        }
    ]
}        

