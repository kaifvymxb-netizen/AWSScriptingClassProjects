import boto3

import json

region = 'us-east-1'

ec2 = boto3.client('ec2', region_name=region)


def lambda_handler(event, context):

    response = ec2.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': [
                    'stopped',
                ],
            },
        ],
    )

    listofinstanceids = []

    for reservation in response["Reservations"]:
        instances = reservation["Instances"]

        for instance in instances:
            print(instance["InstanceId"])
            listofinstanceids.append(instance["InstanceId"])

    start_response = "Nothing needed to be started"

    if len(listofinstanceids) != 0:
        start_response = ec2.start_instances(InstanceIds=listofinstanceids, DryRun=False)

    print(start_response)

    return {
        'statusCode': 200,
        'body': json.dumps(start_response)
    }
