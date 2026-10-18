import boto3, json, argparse, string, random
from botocore.exceptions import ClientError

parser = argparse.ArgumentParser(description='Naming and creating an S3 bucket for a static website')
parser.add_argument('--sitename', type=str, help='Name of the S3 bucket to create for the static website')

args = parser.parse_args()

if args.sitename:
    myBucketName = args.sitename
else:
    random_suffix = "".join(random.choices(string.ascii_lowercase, k=10))
    myBucketName = 'my-static-website-bucket-' + random_suffix

print("Using bucket name:", myBucketName)

# Building a static website in S3 with Python and Boto3
client = boto3.client('s3')

#Deepseek decided to put what was written in the old builds3website.py file into a function
def create_bucket(client, myBucketName):
    try:
        client.create_bucket(Bucket=myBucketName)
        client.delete_public_access_block(Bucket=myBucketName)
        bucket_policy = {
            'Version': '2012-10-17',
            'Statement': [{
                'Sid': 'AddPerm',
                'Effect': 'Allow',
                'Principal': '*',
                'Action': ['s3:GetObject'],
                'Resource': "arn:aws:s3:::%s/*" % myBucketName
            }]
        }
        client.put_bucket_policy(Bucket=myBucketName, Policy=json.dumps(bucket_policy))
        put_bucket_response = client.put_bucket_website(
            Bucket=myBucketName,
            WebsiteConfiguration={
                'ErrorDocument': {'Key': 'error.html'},
                'IndexDocument': {'Suffix': 'index.html'},
            }
        )
        html_files = ["index.html", "error.html"]
        for file in html_files:
            with open(file, "rb") as f:
                body = f.read()
                client.put_object(
                    Body=body,
                    Bucket=myBucketName,
                    Key=file,
                    ContentType='text/html')
        print("Successfully created static website for bucket:", myBucketName)
    except client.exceptions.BucketAlreadyExists as err:
        print("Bucket {} already exists!".format(err.response['Error']['BucketName']))
    except ClientError as err:
        error_code = err.response['Error']['Code']
        if error_code == 'InvalidToken':
            print("Invalid Token: please update your credentials file (~/.aws/credentials) and try again.")
        else:
            print("Error Code:", error_code)


create_bucket(client, myBucketName)
