#Use Boto3 to List IAM Roles and Policies
import boto3, datetime, json, datetime, argparse


parser = argparse.ArgumentParser(description='List IAM Roles and Policies')
parser.add_argument('--rolename', type=str, help='Name of the IAM role to describe')
parser.add_argument('--cutoff', type=int, default=90, help='Number of days to look back for role creation date (default: 90)')

args = parser.parse_args()

iam = boto3.client('iam')
now_utc = datetime.datetime.now(datetime.timezone.utc)   # ← current UTC time
cutoff_date  = now_utc - datetime.timedelta(days=args.cutoff)        # ← specified days ago, defualt 90 days ago
#could make this a function ^
if args.rolename:
    role_name = args.rolename
    try:
        role = iam.get_role(RoleName=role_name)
        if role['Role']['CreateDate'] > cutoff_date: 
            #print("Role:", role['Role']['RoleName'])
            #print("Created:", role['Role']['CreateDate'])
            #print("Path:", role['Role']['Path'])
            #print("ARN:", role['Role']['Arn'])
            #print("Assume Role Policy Document:")
            #print(json.dumps(role['Role']['AssumeRolePolicyDocument'], indent=4))
    except:
        print("Role {} does not exist!".format(role_name))
else:
    roles = iam.list_roles()
    for role in roles['Roles']:
        if role['CreateDate'] > cutoff_date:
            #print("Role:", role['RoleName'])
            #print("Created:", role['CreateDate'])
            #print("Path:", role['Path'])
            #print("ARN:", role['Arn'])
            #print()