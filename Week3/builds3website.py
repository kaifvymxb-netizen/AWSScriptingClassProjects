import boto3, json

# Building a static website in S3 with Python and Boto3
s3client = boto3.client('s3')
myBucketName = 'my-static-website-bucket-1928'
s3client.create_bucket(Bucket=myBucketName)
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