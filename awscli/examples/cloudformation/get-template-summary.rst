**To display a template summary**

The following ``get-template-summary`` example displays summary information about the resources and metadata for the specified template file. ::

    aws cloudformation get-template-summary \
        --template-body file://template.yaml

Contents of ``template.yaml``::

    AWSTemplateFormatVersion: "2010-09-09"
    Description: A VPC and subnets.
    Resources:
      VPC:
        Type: AWS::EC2::VPC
        Properties:
          CidrBlock: 10.0.0.0/16
      Subnet1:
        Type: AWS::EC2::Subnet
        Properties:
          VpcId: !Ref VPC
          CidrBlock: 10.0.0.0/24
      Subnet2:
        Type: AWS::EC2::Subnet
        Properties:
          VpcId: !Ref VPC
          CidrBlock: 10.0.1.0/24
      RouteTable:
        Type: AWS::EC2::RouteTable
        Properties:
          VpcId: !Ref VPC
      S3Endpoint:
        Type: AWS::EC2::VPCEndpoint
        Properties:
          VpcId: !Ref VPC
          ServiceName: !Sub com.amazonaws.${AWS::Region}.s3
          RouteTableIds:
            - !Ref RouteTable
      Subnet1RouteTableAssociation:
        Type: AWS::EC2::SubnetRouteTableAssociation
        Properties:
          SubnetId: !Ref Subnet1
          RouteTableId: !Ref RouteTable
      Subnet2RouteTableAssociation:
        Type: AWS::EC2::SubnetRouteTableAssociation
        Properties:
          SubnetId: !Ref Subnet2
          RouteTableId: !Ref RouteTable
      DynamoDBEndpoint:
        Type: AWS::EC2::VPCEndpoint
        Properties:
          VpcId: !Ref VPC
          ServiceName: !Sub com.amazonaws.${AWS::Region}.dynamodb
          RouteTableIds:
            - !Ref RouteTable

Output::

    {
        "Parameters": [],
        "Description": "A VPC and subnets.",
        "ResourceTypes": [
            "AWS::EC2::VPC",
            "AWS::EC2::Subnet",
            "AWS::EC2::Subnet",
            "AWS::EC2::RouteTable",
            "AWS::EC2::VPCEndpoint",
            "AWS::EC2::SubnetRouteTableAssociation",
            "AWS::EC2::SubnetRouteTableAssociation",
            "AWS::EC2::VPCEndpoint"
        ],
        "Version": "2010-09-09"
    }

For more information, see `Working with CloudFormation templates <https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-guide.html>`__ in the *AWS CloudFormation User Guide*.
