import boto3, csv

def Get_Instances(Name, Value):
    ec2_client = boto3.client('ec2')
    paginator = ec2_client.get_paginator('describe_instances')
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
        for instance in page['Reservations']:
            response.append(instance)
    return response

def CSV_Writer(header, content):
    with open('export.csv', 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=header)
        writer.writeheader()
        for row in content:
            writer.writerow(row)

def main():
    header = ['InstanceId', 'InstanceName', 'InstanceType', 'State', 'PublicIpAddress', 'MonitoringState']
    content = []
    for reservation in Get_Instances('instance-type', 't2.micro'):
        for instance in reservation['Instances']:
            name = ''
            for tag in instance.get('Tags', []):
                if tag['Key'] == 'Name':
                    name = tag['Value']
            state = instance['State']['Name']
            monitoring = instance['Monitoring']['State']
            print(f"Instance Name: {name}")
            print(f"State: {state}")
            print(f"Monitoring State: {monitoring}")
            content.append({
                'InstanceId': instance['InstanceId'],
                'InstanceName': name,
                'InstanceType': instance['InstanceType'],
                'State': state,
                'PublicIpAddress': instance.get('PublicIpAddress', "N/A"),
                'MonitoringState': monitoring,
            })
    CSV_Writer(header, content)
    print(f"Wrote {len(content)} row(s) to export.csv")

if __name__ == "__main__":
    main()