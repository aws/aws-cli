**To list the metrics for Amazon EC2**

The following example uses the ``list-metrics`` command to list the metrics for Amazon EC2::

  aws cloudwatch list-metrics --namespace "AWS/EC2"

Output::

{
"Metrics": [
{
"Namespace": "AWS/EC2",
"Dimensions": [
{
"Name": "InstanceId",
"Value": "i-dd8855ba"
}
],
"MetricName": "DiskReadBytes"
},
{
"Namespace": "AWS/EC2",
"Dimensions": [
{
"Name": "InstanceId",
"Value": "i-0b12b76c"
}
],
"MetricName": "CPUUtilization"
},
{
"Namespace": "AWS/EC2",
"Dimensions": [],
"MetricName": "NetworkIn"
},
{
"Namespace": "AWS/EC2",
"Dimensions": [
{
"Name": "InstanceId",
"Value": "i-e31dbd84"
}
],
"MetricName": "DiskReadOps"
},
{
"Namespace": "AWS/EC2",
"Dimensions": [
{
"Name": "InstanceId",
"Value": "i-13bf6574"
}
],
"MetricName": "DiskWriteBytes"
},
{
"Namespace": "AWS/EC2",
"Dimensions": [
{
"Name": "InstanceId",
"Value": "i-2840c24f"
}
],
"MetricName": "DiskReadOps"
},
{
"Namespace": "AWS/EC2",
"Dimensions": [
{
"Name": "InstanceId",
"Value": "i-9960c1fe"
}
],
"MetricName": "NetworkOut"
}
}
