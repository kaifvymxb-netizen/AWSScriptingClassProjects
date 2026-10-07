import boto3
import json

def main():
    image_id = get_latest_linux_2_ami()
    print(f"Retreieval Successful.")
    print(f"Latest Amazon Linux 2 AMI ID: {image_id}")

    # Create the security group first
    sg_name = 'WebSG'
    create_ssh_http_security_group(sg_name=sg_name)  # Creates the security group if needed
    print(f"Security group configured: {sg_name}")

    # Now create the instance with the security group
    instance_id = create_ec2_instance(
        image_id,
        SecurityGroups=['WebSG'],
        KeyName='vockey',
        UserDataFile='user_data.txt'
    ) # I saw what this looked like when you just pasted the user data in this file, and I was viscerally offended by what it looked like. I asked nemotron to do it by file instead.

    print(f"EC2 Instance Creation Successful. Instance ID: {instance_id}")

    ec2 = boto3.resource('ec2')
    instance = ec2.Instance(instance_id) #create instance object using instance id

    instance.wait_until_running()#wait until instance is running
    instance.reload()#reload instance attributes to get updated information

    print_instance_details(instance)#print instance details
    print(f"Instance is now running and details are now updated.")
    tags_to_addDict = {"Name":"Week3Instance", "Week":"Week3", "OwnerName":"Kai"} #This would be a good place to use parse args for, but for now it is hardcoded.
    give_tags_to_instance(instance_id, tags_to_addDict)#give tags to instance
    tag_description_text = describe_instance_tags(instance_id)
    print(tag_description_text)#print instance tags

    # Test Get_Instances with instance-type filter
    print("\n--- Testing Get_Instances filter ---")
    reservations = Get_Instances('instance-type', 't2.micro')
    for reservation in reservations:
        for inst in reservation['Instances']:
            name = ''
            for tag in inst.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
            print(f"Instance Name: {name}")
            print(f"State: {inst['State']['Name']}")
            print(f"Monitoring State: {inst['Monitoring']['State']}")

    #instance.terminate()
    #instance.wait_until_terminated()
    print(f"Instance {instance.id} has been terminated.")


def get_latest_linux_2_ami():

    client = boto3.client('ec2')

    Filters = [
        {
            'Name': 'description',
            'Values': ['Amazon Linux 2 AMI*']
        },
        {
            'Name': 'architecture',
            'Values': ['x86_64']
        },
        {
            'Name': 'owner-alias',
            'Values': ['amazon']
        }
    ]
    image_data = client.describe_images(Filters=Filters)
    image_id = image_data['Images'][0]['ImageId']
    return image_id

def create_ec2_instance(image_id, SecurityGroups=None, KeyName=None, UserDataFile=None):
    ec2 = boto3.client('ec2')

    run_kwargs = {
        'ImageId': image_id,
        'InstanceType': 't2.micro',
        'MinCount': 1,
        'MaxCount': 1,
        'DryRun': False
    }

    if SecurityGroups is not None:
        run_kwargs['SecurityGroups'] = SecurityGroups
    if KeyName is not None:
        run_kwargs['KeyName'] = KeyName
    if UserDataFile is not None:
        with open(UserDataFile, 'r') as f:
            run_kwargs['UserData'] = f.read()

    response = ec2.run_instances(**run_kwargs)
    return response['Instances'][0]['InstanceId']

def print_instance_details(instance):
    print(f"Instance ID: {instance.id}")
    print(f"State: {instance.state['Name']}")
    print(f"Public DNS: {instance.public_dns_name}")
    print(f"Public IP: {instance.public_ip_address}")

def give_tags_to_instance(instance_id, tags):
    ec2 = boto3.client('ec2')
    tag_list = [{'Key': key, 'Value': value} for key, value in tags.items()]
    ec2.create_tags(Resources=[instance_id], Tags=tag_list) 

def describe_instance_tags(instance_id):
    ec2 = boto3.client('ec2')
    response = ec2.describe_tags(Filters=[{'Name': 'resource-id', 'Values': [instance_id]}])
    return response['Tags']

def Get_Instances(Name, Value):
    ec2 = boto3.client('ec2')
    paginator = ec2.get_paginator('describe_instances')
    page_list = paginator.paginate(
        Filters=[
            {
                'Name': Name,
                'Values': [Value],
            },
        ]
    )
    response = []
    for page in page_list:
        for reservation in page['Reservations']:
            response.append(reservation)
    return response

def create_ssh_http_security_group(vpc_id=None, sg_name='WebSG', sg_description='Security group allowing SSH and HTTP access'):
    """Create a security group with inbound rules for SSH (port 22) and HTTP (port 80).
    
    Args:
        vpc_id: VPC ID where the security group will be created. Defaults to the account's default VPC.
        sg_name: Name of the security group. Defaults to 'WebSG'.
        sg_description: Description of the security group. Defaults to 'Security group allowing SSH and HTTP access'.
    
    Returns:
        The ID of the created security group.
    """
    ec2 = boto3.client('ec2')
    
    # Check if security group already exists and delete it
    try:
        existing_sgs = ec2.describe_security_groups(Filters=[{'Name': 'group-name', 'Values': [sg_name]}])
        if existing_sgs['SecurityGroups']:
            sg_to_delete = existing_sgs['SecurityGroups'][0]
            print(f'Deleting existing security group: {sg_to_delete["GroupId"]}')
            ec2.delete_security_group(GroupId=sg_to_delete['GroupId'])
    except Exception as e:
        print(f'No existing security group to delete: {e}')
    
    # Build the create_security_group parameters
    create_kwargs = {
        'GroupName': sg_name,
        'Description': sg_description
    }
    
    # Only add VpcId if explicitly provided
    if vpc_id is not None:
        create_kwargs['VpcId'] = vpc_id
    
    # Create the security group
    response = ec2.create_security_group(**create_kwargs)
    sg_id = response['GroupId']
    print(f'Created security group: {sg_id}')
    
    # Add inbound rule for SSH (port 22)
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )
    print('Added SSH (port 22) inbound rule')

    # Add inbound rule for HTTP (port 80)
    ec2.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )
    print('Added HTTP (port 80) inbound rule')
    
    return sg_id

if __name__ == "__main__":
    main()