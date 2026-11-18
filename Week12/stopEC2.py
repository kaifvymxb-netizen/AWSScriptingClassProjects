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

                'running', 

            ] 

        }, 

    ], 

    ) 

    listofinstanceids = [] 

    for reservation in response["Reservations"]: 

        instances = reservation["Instances"] 

     

        for instance in instances: 

             print(instance["InstanceId"]) 

             listofinstanceids.append(instance["InstanceId"]) 

     

    stop_response = "Nothing needed to be stopped" 

    if len(listofinstanceids) != 0: 

        stop_response = ec2.stop_instances(InstanceIds=listofinstanceids,DryRun=False) 

    print(stop_response) 

    return { 

        'statusCode': 200, 

        'body': json.dumps(stop_response) 

    } 