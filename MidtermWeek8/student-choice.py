#!/usr/bin/env python3
"""List EC2 key pairs and the EC2 instances launched with each one.

A key pair is regional, and an instance stores the key pair name in KeyName.
This script intentionally reports only EC2 instances. It does not inspect
launch templates, launch configurations, Auto Scaling groups, EMR clusters,
or AMIs.
"""

import argparse
import sys
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError

# Errors that mean "not allowed / not available here", not a script bug.
DENIED_ERROR_CODES = {
    "AccessDenied",
    "AccessDeniedException",
    "AuthFailure",
    "OptInRequired",
    "UnauthorizedOperation",
}


class KeyPairNotFoundError(Exception):
    """Raised when one or more requested key pairs do not exist."""


def missing_key_message(missing, location):
    """Build a readable error for one or more missing key pairs."""
    names = ", ".join(f"'{name}'" for name in missing)
    noun = "Key pair" if len(missing) == 1 else "Key pairs"
    verb = "does" if len(missing) == 1 else "do"
    return f"{noun} {names} {verb} not exist in {location}."


def is_denied(error):
    """Return True when a ClientError is a permissions/availability error."""
    return error.response.get("Error", {}).get("Code") in DENIED_ERROR_CODES


def error_code(error):
    """Return a short error code for a ClientError."""
    return error.response.get("Error", {}).get("Code", "unknown error")


def list_key_pairs(ec2, wanted_names, region, require_all):
    """Return the key pairs in one region, optionally filtered by name.

    When require_all is True, raise KeyPairNotFoundError if any requested
    key pair is absent. When it is False (--all-regions), the caller decides
    whether a key pair was missing everywhere.
    """
    key_pairs = ec2.describe_key_pairs().get("KeyPairs", [])
    if not wanted_names:
        return key_pairs

    wanted = set(wanted_names)
    found = {pair["KeyName"] for pair in key_pairs}
    missing = sorted(wanted - found)

    if missing and require_all:
        raise KeyPairNotFoundError(missing_key_message(missing, region))

    return [pair for pair in key_pairs if pair["KeyName"] in wanted]


def collect_instances(ec2, key_names, associations, notes):
    """Find EC2 instances launched with one of these key pairs."""
    try:
        paginator = ec2.get_paginator("describe_instances")
        pages = paginator.paginate(
            Filters=[{"Name": "key-name", "Values": sorted(key_names)}]
        )
        for instance in pages.search("Reservations[].Instances[]"):
            key_name = instance.get("KeyName")
            if key_name not in key_names:
                continue
            associations[key_name].append(
                {
                    "id": instance["InstanceId"],
                    "state": instance["State"]["Name"],
                    "type": instance.get("InstanceType", "unknown type"),
                }
            )
    except ClientError as error:
        if is_denied(error):
            notes.append(f"EC2 instances not inspected: {error_code(error)}")
        else:
            raise


def audit_region(session, region, wanted_names, require_all=True):
    """Audit one region.

    Returns (key_pairs, associations, notes), or None when key pairs cannot
    be listed in this region. Raises KeyPairNotFoundError when require_all is
    True and a requested key pair is absent.
    """
    ec2 = session.client("ec2", region_name=region)

    try:
        key_pairs = list_key_pairs(ec2, wanted_names, region, require_all)
    except ClientError as error:
        if is_denied(error):
            print(
                f"Region: {region}\n"
                f"  cannot list key pairs ({error_code(error)}); skipped\n"
            )
            return None
        raise

    if not key_pairs:
        return [], {}, []

    key_names = {pair["KeyName"] for pair in key_pairs}
    associations = defaultdict(list)
    notes = []

    collect_instances(ec2, key_names, associations, notes)

    return key_pairs, associations, notes


def print_region(region, key_pairs, associations, notes):
    """Print one region's key pairs and their EC2 instances."""
    print(f"Region: {region}")

    if not key_pairs:
        print("  (no key pairs found)\n")
        return

    for pair in sorted(key_pairs, key=lambda item: item["KeyName"].lower()):
        created = pair.get("CreateTime")
        created_text = f", created {created:%Y-%m-%d}" if created else ""
        print(
            f"  {pair['KeyName']} "
            f"({pair.get('KeyPairId', 'unknown id')}, "
            f"{pair.get('KeyType', 'unknown type')}{created_text})"
        )

        instances = associations.get(pair["KeyName"], [])
        if not instances:
            print("      no EC2 instances found")
        else:
            for instance in instances:
                print(
                    f"      {instance['id']} "
                    f"({instance['state']}, {instance['type']})"
                )
        print()

    if notes:
        for note in notes:
            print(f"  note: {note}")
        print()


def get_regions(session, args):
    """Return the regions to audit."""
    if args.region:
        return [args.region]

    if not args.all_regions:
        return [session.region_name or "us-east-1"]

    try:
        ec2 = session.client("ec2")
        return [region["RegionName"] for region in ec2.describe_regions()["Regions"]]
    except ClientError as error:
        if is_denied(error):
            print(
                f"Cannot list regions ({error_code(error)}); "
                f"using {session.region_name or 'us-east-1'} only."
            )
            return [session.region_name or "us-east-1"]
        raise


def main():
    parser = argparse.ArgumentParser(
        description="List EC2 key pairs and the EC2 instances launched with each"
    )
    parser.add_argument(
        "--key",
        action="append",
        help="Only audit this key pair name (repeat for multiple names)",
    )

    region_group = parser.add_mutually_exclusive_group()
    region_group.add_argument(
        "--region",
        help="Region to audit (default: the region configured in your AWS session)",
    )
    region_group.add_argument(
        "--all-regions",
        action="store_true",
        help="Audit every region; regions without permission are skipped",
    )

    args = parser.parse_args()

    session = boto3.Session(region_name=args.region) if args.region else boto3.Session()
    regions = get_regions(session, args)

    total_key_pairs = 0
    total_instances = 0
    successful_regions = 0
    skipped_regions = 0
    found_requested = set()

    for region in regions:
        try:
            result = audit_region(
                session,
                region,
                args.key,
                require_all=not args.all_regions,
            )
        except KeyPairNotFoundError as error:
            print(f"Error: {error}")
            return 1

        if result is None:
            skipped_regions += 1
            continue

        key_pairs, associations, notes = result
        successful_regions += 1
        total_key_pairs += len(key_pairs)
        total_instances += sum(len(items) for items in associations.values())
        found_requested.update(pair["KeyName"] for pair in key_pairs)
        print_region(region, key_pairs, associations, notes)

    if args.key:
        missing = sorted(set(args.key) - found_requested)
        if missing:
            print(f"Error: {missing_key_message(missing, 'any audited region')}")
            return 1

    print(
        f"Summary: {total_key_pairs} key pair(s), "
        f"{total_instances} EC2 instance association(s), "
        f"{successful_regions} region(s) audited, "
        f"{skipped_regions} region(s) skipped."
    )
    return 0 if successful_regions else 1


if __name__ == "__main__":
    sys.exit(main())
