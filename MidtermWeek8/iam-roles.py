#Use Boto3 to list IAM roles created in the last 90 days and the policies attached to each one
import argparse
import datetime
import sys

import boto3
from botocore.exceptions import ClientError

CUTOFF_DAYS = 90

# IAM raises "AccessDenied"; some services use "AccessDeniedException". 
# This probably represents a best practices for defining anticipated error codes for except handling that deepseek/ai knows about that I haven't seen yet
DENIED_ERROR_CODES = {"AccessDenied", "AccessDeniedException"}


def get_role_managed_policy_names(iam, role_name):
    """Return the names of the managed policies attached to one role.

    Uses list_attached_role_policies (per-role) rather than list_policies.
    Returns None when the caller is not allowed to read them.
    """
    paginator = iam.get_paginator("list_attached_role_policies")
    try:
        return [
            name
            for name in paginator.paginate(RoleName=role_name).search(
                "AttachedPolicies[].PolicyName"
            )
        ]
    except ClientError as error:
        if error.response["Error"]["Code"] in DENIED_ERROR_CODES:
            return None
        raise


def get_role_inline_policy_names(iam, role_name):
    """Return the names of the inline (unmanaged) policies embedded in one role.

    Uses list_role_policies (per-role) rather than list_policies.
    Returns None when the caller is not allowed to read them.
    """
    paginator = iam.get_paginator("list_role_policies")
    try:
        return [
            name
            for name in paginator.paginate(RoleName=role_name).search("PolicyNames[]")
        ]
    except ClientError as error:
        if error.response["Error"]["Code"] in DENIED_ERROR_CODES:
            return None
        raise


def print_role_and_policies(iam, role):
    """Print one role and every policy attached to it.

    The role line is printed before any policy lookup runs, so a role is
    never skipped just because its policies could not be read.
    """
    created = role["CreateDate"]
    print(f"Role: {role['RoleName']} (created {created:%Y-%m-%d %H:%M %Z})")

    lookups = (
        ("managed", get_role_managed_policy_names, "iam:ListAttachedRolePolicies"),
        ("unmanaged", get_role_inline_policy_names, "iam:ListRolePolicies"),
    )

    for kind, fetch, permission in lookups:
        names = fetch(iam, role["RoleName"])
        if names is None:
            print(f"  (cannot see {kind} policies: access denied, requires {permission})")
        elif not names:
            print(f"  (no {kind} policies attached)")
        else:
            for name in names:
                print(f"  {name}")

    print()


def get_all_roles(iam):
    """Return every role in the account."""
    paginator = iam.get_paginator("list_roles")
    return list(paginator.paginate().search("Roles[]"))


def main():
    parser = argparse.ArgumentParser(
        description="List IAM roles created in the last N days and their policies"
    )
    parser.add_argument(
        "--cutoff",
        type=int,
        default=CUTOFF_DAYS,
        help=f"Number of days to look back for role creation date (default: {CUTOFF_DAYS})",
    )
    parser.add_argument(
        "--rolename",
        type=str,
        help="Only show this role",
    )
    args = parser.parse_args()

    iam = boto3.client("iam")
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    cutoff_date = now_utc - datetime.timedelta(days=args.cutoff)

    if args.rolename:
        try:
            roles = [iam.get_role(RoleName=args.rolename)["Role"]]
        except iam.exceptions.NoSuchEntityException:
            print(f"Role {args.rolename} was not found.")
            return 1
        except ClientError as error:
            if error.response["Error"]["Code"] in DENIED_ERROR_CODES:
                print(f"Access denied: you cannot read the role {args.rolename}.")
                return 1
            raise
    else:
        try:
            roles = get_all_roles(iam)
        except ClientError as error:
            if error.response["Error"]["Code"] in DENIED_ERROR_CODES:
                print("Access denied: you do not have permission to list IAM roles.")
                print("This script needs iam:ListRoles before it can show anything.")
            else:
                raise
            return 1

    recent = [role for role in roles if role["CreateDate"] > cutoff_date]

    if not recent:
        if args.rolename:
            role = roles[0]
            print(
                f"Role: {role['RoleName']} (created {role['CreateDate']:%Y-%m-%d %H:%M %Z})"
            )
            print(
                f"  (older than the {args.cutoff} day cutoff, raise --cutoff to include its policies)"
            )
        else:
            print(f"No roles were created in the last {args.cutoff} days.")
        return 0

    for role in recent:
        print_role_and_policies(iam, role)

    return 0


if __name__ == "__main__":
    sys.exit(main())
