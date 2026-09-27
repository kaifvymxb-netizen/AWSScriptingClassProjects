
import boto3
import json

def main():
    image_id = get_latest_linux_2_ami()
    print(f"Retreieval Successful.")
    print(f"Latest Amazon Linux 2 AMI ID: {image_id}")

    instance_id = create_ec2_instance(image_id) #create instance and return instance id
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
    instance.terminate()
    instance.wait_until_terminated()
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

def create_ec2_instance(image_id):
    ec2 = boto3.client('ec2')

    response = ec2.run_instances(
        ImageId=image_id,
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        DryRun=False    
        )
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

if __name__ == "__main__":
    main()