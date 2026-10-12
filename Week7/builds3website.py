import boto3, json, argparse

parser = argparse.ArgumentParser(description='Naming and creating an S3 bucket for a static website')
parser.add_argument('--site-name', dest='bucket_name', type=str, required=True, help='Name of the S3 bucket to create for the static website')

args = parser.parse_args()
myBucketName = args.bucket_name

# Building a static website in S3 with Python and Boto3
# NOTE: Do NOT specify region_name='us-east-1' when creating the client,
# as this triggers IllegalLocationConstraintException. Let boto3 use the
# default region from the AWS config (typically us-east-1).
# For regions other than us-east-1, CreateBucketConfiguration with
# LocationConstraint is required (handled below).

s3client = boto3.client('s3')

session = boto3.session.Session()
region = session.region_name

if region == 'us-east-1':
    # us-east-1: create bucket without LocationConstraint
    s3client.create_bucket(Bucket=myBucketName)
else:
    # Other regions: must specify CreateBucketConfiguration with LocationConstraint
    s3client.create_bucket(
        Bucket=myBucketName,
        CreateBucketConfiguration={'LocationConstraint': region}
    )

s3client.delete_public_access_block(Bucket=myBucketName)
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

s3client.put_bucket_policy(Bucket=myBucketName, Policy=json.dumps(bucket_policy))
put_bucket_response = s3client.put_bucket_website( 
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
           s3client.put_object(                                                                                                                                                                                                                 
               Body=body,                                                                                                                                                                                                                       
               Bucket=myBucketName,                                                                                                                                                                                                             
               Key=file,                                                                                                                                                                                                                        
               ContentType='text/html' )