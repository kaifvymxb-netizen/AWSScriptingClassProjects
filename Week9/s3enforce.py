import boto3


def CreateBucket(bucket_name):
    s3 = boto3.client('s3')
    s3.create_bucket(Bucket=bucket_name)


def DeleteBucket(bucket_name):
    s3 = boto3.client('s3')
    s3.delete_bucket(Bucket=bucket_name)


def EnforceVersioning(bucket_name):
    s3 = boto3.client('s3')
    s3.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={
            'MFADelete': 'Disabled',
            'Status': 'Enabled',
        },
    )


def SetBucketPolicy(bucket_name, policy):
    s3 = boto3.client('s3')
    s3.put_bucket_policy(Bucket=bucket_name, Policy=policy)


if __name__ == '__main__':
    bucket_name = 'my-week9-enforce-bucket'
    CreateBucket(bucket_name)
    EnforceVersioning(bucket_name)
