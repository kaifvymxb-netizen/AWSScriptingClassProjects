import boto3

def create_sns_topic(topic_name):
    sns_client = boto3.client('sns')
    response = sns_client.create_topic(Name=topic_name)
    return response['TopicArn']
def subscribe_sns_topic(topic_arn, protocol, endpoint):
    sns_client = boto3.client('sns')
    response = sns_client.subscribe(
        TopicArn=topic_arn,
        Protocol=protocol,
        Endpoint=endpoint
    )
    return response['SubscriptionArn']