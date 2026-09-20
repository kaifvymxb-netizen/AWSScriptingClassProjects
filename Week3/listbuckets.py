import boto3
s3 = boto3.client('s3')
# Creating Prompts:  how would you retrieve the list of objects in every bucket?  
def list_all_buckets_and_their_objects(): 
    with open('mybuckets.txt', 'w') as out:                                                                                                                                                                                                      
       out.write('Buckets and objects:\n')                                                                                                                                                                                                      
       # collect all bucket names                                                                                                                                                                                                               
       all_buckets = []                                                                                                                                                                                                                         
       for bucket_summary in s3.get_paginator('list_buckets').paginate():                                                                                                                                                                       
           all_buckets.extend([b['Name'] for b in bucket_summary['Buckets']])                                                                                                                                                                   
       for bucket_name in all_buckets:                                                                                                                                                                                                          
           out.write(f'\nBucket: {bucket_name}\n')                                                                                                                                                                                              
           for page in s3.get_paginator('list_objects_v2').paginate(Bucket=bucket_name):                                                                                                                                                        
               if 'Contents' in page:                                                                                                                                                                                                           
                   for obj in page['Contents']:                                                                                                                                                                                                 
                       out.write(f'  {obj["Key"]}\n')                                                                                                                                                                                           
               else:                                                                                                                                                                                                                            
                   out.write('  (empty)\n')

if __name__ == '__main__':                                                                                                                                                                                                                   
       list_all_buckets_and_their_objects()                