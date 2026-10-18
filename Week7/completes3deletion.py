import boto3

s3 = boto3.client('s3')

buckets = s3.list_buckets().get('Buckets', [])

for bucket in buckets:
    bucket_name = bucket['Name']
    print(f"Deleting bucket: {bucket_name}")

    response = s3.list_objects_v2(Bucket=bucket_name)

    while True:
        for obj in response.get('Contents', []):
            s3.delete_object(Bucket=bucket_name, Key=obj['Key'])
            print(f"  Deleted object: {obj['Key']}")

        if response.get('IsTruncated'):
            response = s3.list_objects_v2(
                Bucket=bucket_name,
                ContinuationToken=response['NextContinuationToken']
            )
        else:
            break

    s3.delete_bucket(Bucket=bucket_name)
    print(f"Deleted bucket: {bucket_name}")

print("All buckets deleted.")
