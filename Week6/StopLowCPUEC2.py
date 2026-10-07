import boto3, ec2, SNS


DRYRUN = False
def main():
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']

    ec2_client = boto3.client('ec2')
    print(f"Account ID: {account_id}")

    image_id = ec2.get_latest_linux_2_ami()

    instance_id = ec2.create_ec2_instance(image_id, SecurityGroups=['WebSG'], KeyName='vockey', UserDataFile='user_data.txt')

    ec2_resource = boto3.resource('ec2')
    instance = ec2_resource.Instance(instance_id)
    instance.wait_until_running()
    instance.reload()

    topic_arn = SNS.create_sns_topic('LowCPUAlarm')
    SNS.subscribe_sns_topic(topic_arn, 'email', 'KaiFVy.mx.b@gmail.com')
    put_metric_alarm_low_usage(instance_id, account_id)
    print(f"Alarm for instance {instance_id} has been set.")

def put_metric_alarm_low_usage(instance_id, account_id):
    cw_client = boto3.client('cloudwatch')
    response = cw_client.put_metric_alarm( 
        AlarmName='Web_Server_LOW_CPU_Utilization', 
        ComparisonOperator='LessThanOrEqualToThreshold', 
        EvaluationPeriods=1, 
        MetricName='CPUUtilization', 
        Namespace='AWS/EC2', 
        Period=300, 
        Statistic='Average', 
        Threshold=10.0, 
        ActionsEnabled=True, 
        AlarmActions=[ 
            f'arn:aws:sns:us-east-1:{account_id}:LowCPUAlarm',
            f'arn:aws:swf:us-east-1:{account_id}:action/actions/AWS_EC2.InstanceId.Stop/1.0'
        ], 
        AlarmDescription='Alarm when server CPU is lower than 10%', 
        Dimensions=[ 
        { 
            'Name': 'InstanceId', 
            'Value': instance_id 
        }
        ]
    )

if __name__ == "__main__":
    main()