import boto3    
sts = boto3.client('sts')
hFile = open('credential-check.txt', 'w')
result = sts.get_caller_identity()
print(str(result))
hFile.write(f"Caller Identity: {result['UserId']}\n")
hFile.write(f"Date: {result['ResponseMetadata']['HTTPHeaders']['date']}\n")  
hFile.close()