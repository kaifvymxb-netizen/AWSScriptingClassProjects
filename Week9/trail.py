import boto3
import json

import s3enforce


def main():
    sts_client = boto3.client('sts')
    account_id = sts_client.get_caller_identity()['Account']
    print(f"Account ID: {account_id}")

    bucket_name = 'my-week9-trail-bucket'
    s3enforce.CreateBucket(bucket_name)

    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AWSCloudTrailAclCheck20150319",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:GetBucketAcl",
                "Resource": f"arn:aws:s3:::{bucket_name}"
            },
            {
                "Sid": "AWSCloudTrailWrite20150319",
                "Effect": "Allow",
                "Principal": {"Service": "cloudtrail.amazonaws.com"},
                "Action": "s3:PutObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/AWSLogs/{account_id}/*",
                "Condition": {"StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}}
            }
        ]
    }

    policy_string = json.dumps(policy)
    s3enforce.SetBucketPolicy(bucket_name=bucket_name, policy=policy_string)

    CreateTrail('my-week9-trail', bucket_name)


def CreateTrail(trail_name, bucket_name):
    cloudtrail_client = boto3.client('cloudtrail')

    try:
        response = cloudtrail_client.create_trail(
            Name=trail_name,
            S3BucketName=bucket_name
        )
    except cloudtrail_client.exceptions.TrailAlreadyExistsException:
        print(f"Trail '{trail_name}' already exists, continuing.")
        response = None

    cloudtrail_client.start_logging(Name=trail_name)
    return response


if __name__ == "__main__":
    main()
