#Use Boto3 to report which EC2 security groups are open to the public internet
import argparse
import sys
import urllib.request  # optional: only used by --create to auto-detect your IP

import boto3
from botocore.exceptions import ClientError

# Errors that mean "you are not allowed", as opposed to a bug in the script.
DENIED_ERROR_CODES = {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}

# Inbound source ranges that mean "any address on the internet".
PUBLIC_CIDRS = {"0.0.0.0/0", "::/0"}
WARNING = "WARNING: Open to the public internet!"

# -1 means every protocol; EC2 may also return the numeric protocol number.
PROTOCOL_LABELS = {"-1": "all", "1": "icmp", "6": "tcp", "17": "udp", "58": "icmpv6"}


def describe_all_security_groups(ec2):
    """Return every security group in the account."""
    paginator = ec2.get_paginator("describe_security_groups")
    return list(paginator.paginate().search("SecurityGroups[]"))


def describe_one_security_group(ec2, group_name):
    """Return the single security group named group_name, or None if it is gone.

    A missing name is a normal outcome here, so it is turned into None and the
    caller prints the message. Any other error still raises.
    """
    try:
        response = ec2.describe_security_groups(GroupNames=[group_name])
    except ClientError as error:
        if error.response["Error"]["Code"] == "InvalidGroup.NotFound":
            return None
        raise
    groups = response["SecurityGroups"]
    return groups[0] if groups else None


def format_ports(protocol, from_port, to_port):
    """Return a readable port description for one permission."""
    if protocol == "-1" or from_port is None or to_port is None:
        return "all ports"
    if from_port == to_port:
        return str(from_port)
    return f"{from_port}-{to_port}"


def iter_sources(permission):
    """Yield (source_label, is_public) for every source in one permission.

    The allowed sources live in four separate keys of each IpPermissions entry:
    IpRanges (IPv4 CIDR), Ipv6Ranges (IPv6 CIDR), PrefixListIds and
    UserIdGroupPairs. Only the two CIDR lists can be open to the internet.
    """
    for ip_range in permission.get("IpRanges", []):
        cidr = ip_range["CidrIp"]
        yield cidr, cidr in PUBLIC_CIDRS

    for ip_range in permission.get("Ipv6Ranges", []):
        cidr = ip_range["CidrIpv6"]
        yield cidr, cidr in PUBLIC_CIDRS

    for prefix_list in permission.get("PrefixListIds", []):
        yield f"prefix list {prefix_list['PrefixListId']}", False

    for pair in permission.get("UserIdGroupPairs", []):
        label = pair.get("GroupName") or pair.get("GroupId")
        yield f"security group {label}", False


def iter_inbound_rules(security_group):
    """Yield (protocol, ports, source, is_public) for all inbound rules."""
    for permission in security_group.get("IpPermissions", []):
        protocol = permission.get("IpProtocol", "-1")
        ports = format_ports(
            protocol, permission.get("FromPort"), permission.get("ToPort")
        )
        sources = list(iter_sources(permission))
        if not sources:
            yield protocol, ports, "(no source)", False
            continue
        for source, is_public in sources:
            yield protocol, ports, source, is_public


def print_security_group(security_group):
    """Print one security group's inbound rules. Returns True if it is open."""
    name = security_group.get("GroupName", "(no name)")
    group_id = security_group.get("GroupId", "unknown")
    print(f"Security group: {name} ({group_id})")
    if security_group.get("Description"):
        print(f"  description: {security_group['Description']}")

    rules = list(iter_inbound_rules(security_group))
    if not rules:
        print("  inbound: no inbound rules")
        print()
        return False

    is_open = False
    print("  inbound:")
    for protocol, ports, source, is_public in rules:
        protocol_text = PROTOCOL_LABELS.get(protocol, protocol)
        ports_text = "all ports" if ports == "all ports" else f"port {ports}"
        line = f"    {protocol_text:<6} {ports_text:<16} from {source}"
        if is_public:
            is_open = True
            line += f"  {WARNING}"
        print(line)

    print()
    return is_open


def print_report(security_groups):
    """Print every security group, then a one-line summary of the open ones."""
    open_groups = [group for group in security_groups if print_security_group(group)]

    if open_groups:
        print(
            f"{len(open_groups)} of {len(security_groups)} security group(s) allow "
            "traffic from the public internet:"
        )
        for group in open_groups:
            print(f"  {group.get('GroupName')} ({group.get('GroupId')})")
    else:
        print(
            f"None of the {len(security_groups)} security group(s) allow traffic "
            "from the public internet."
        )


# ---------------------------------------------------------------------------
# The helpers below, through create_lab_groups, exist only to support the
# optional --create flag. None of them are needed for the required behavior of
# this script: listing security groups and flagging the ones that are open to
# the public internet. -Deepseek
# In fact, I should consider making them a seperate sg creation script to use in future assignments. - Kai
# ---------------------------------------------------------------------------


def get_default_vpc_id(ec2):
    """Return the default VPC id, or None when the account has no default VPC.

    Optional --create support only; the listing report never needs a VPC id.
    """
    vpcs = ec2.describe_vpcs(Filters=[{"Name": "isDefault", "Values": ["true"]}])["Vpcs"]
    return vpcs[0]["VpcId"] if vpcs else None


def get_public_ip_cidr():
    """Return this machine's public IP as a /32 CIDR, or None if it cannot be read.

    Optional --create support only, and only when --my-ip is not supplied.
    Nothing in the listing report talks to the internet from this machine.
    """
    try:
        with urllib.request.urlopen(
            "https://checkip.amazonaws.com", timeout=10
        ) as response:
            return response.read().decode().strip() + "/32"
    except OSError:
        return None


def describe_permissions(permissions):
    """Return a readable one-line summary of permission dicts, e.g. tcp/22 from 1.2.3.4/32.

    Optional --create support only.
    """
    rules = iter_inbound_rules({"IpPermissions": permissions})
    return ", ".join(
        f"{protocol}/{ports} from {source}" for protocol, ports, source, _ in rules
    )


def authorize_ingress(ec2, group_id, permissions):
    """Add the given inbound rules to an existing group.

    CreateSecurityGroup does not accept IpPermissions, so the rules have to be
    added in a second call. A rule that is already there is not an error here.

    Optional --create support only.
    """
    if not permissions:
        return

    try:
        ec2.authorize_security_group_ingress(
            GroupId=group_id, IpPermissions=permissions
        )
    except ClientError as error:
        if error.response["Error"]["Code"] == "InvalidPermission.Duplicate":
            print("  inbound rule already present")
            return
        raise

    print(f"  inbound rule added: {describe_permissions(permissions)}")

def create_security_group(ec2, group_name, description, vpc_id, permissions):
    """Create one security group with the given inbound rules.

    Safe to re-run: an existing group is reused and its missing rule is added,
    which also repairs a group left without rules by an earlier failure.

    Optional --create support only.
    """
    try:
        response = ec2.create_security_group(
            GroupName=group_name,
            Description=description,
            VpcId=vpc_id,
        )
    except ClientError as error:
        if error.response["Error"]["Code"] != "InvalidGroup.Duplicate":
            raise
        existing = describe_one_security_group(ec2, group_name)
        if existing is None:
            raise
        group_id = existing["GroupId"]
        print(f"{group_name} already exists ({group_id})")
    else:
        group_id = response["GroupId"]
        print(f"Created {group_name} ({group_id})")

    authorize_ingress(ec2, group_id, permissions)
    return group_id

#Lab convenience function.
def create_lab_groups(ec2, name_prefix, my_ip_cidr, vpc_id):
    """Create <prefix>-SSH-SG (my IP only) and <prefix>-HTTP-SG (everyone).

    Optional --create support only; this is the one place the script writes to
    AWS. Everything else it does is read-only.
    """
    ssh_group = f"{name_prefix}-SSH-SG"
    http_group = f"{name_prefix}-HTTP-SG"

    create_security_group(
        ec2,
        ssh_group,
        f"SSH (22) from {my_ip_cidr} only",
        vpc_id,
        [
            {
                "IpProtocol": "tcp",
                "FromPort": 22,
                "ToPort": 22,
                "IpRanges": [{"CidrIp": my_ip_cidr}],
            }
        ],
    )

    create_security_group(
        ec2,
        http_group,
        "HTTP (80) from anywhere",
        vpc_id,
        [
            {
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    )

    # Show the new groups with the same output as the normal report.
    created = [
        group
        for group in (
            describe_one_security_group(ec2, ssh_group),
            describe_one_security_group(ec2, http_group),
        )
        if group is not None
    ]
    if created:
        print()
        print_report(created)


def main(): #I should remember from these that argparse can be in main(). -Kai
    parser = argparse.ArgumentParser(
        description="Show inbound rules for EC2 security groups"
    )
    parser.add_argument(
        "-s",
        "--security-group",
        type=str,
        help="Name of a single security group to inspect (default: all of them)",
    )
    #These next 3 arguments only exist for convenience in the lab; it is not a general-purpose security group creation tool. -Kai
    parser.add_argument(
        "--create",
        metavar="NAME",
        type=str,
        help="For convenience in testing in the lab environment: Create NAME-SSH-SG (SSH from your IP) and NAME-HTTP-SG (HTTP from anywhere)",
    )
    #Next 2 are needed to help the --create option work under certain circumstances. -Kai
    parser.add_argument(
        "--my-ip",
        type=str,
        help="Your public IP as a CIDR such as 203.0.113.5/32 (default: auto-detect)",
    ) 
    parser.add_argument(
        "--vpc-id",
        type=str,
        help="VPC for newly created groups (default: the account's default VPC)",
    )
    args = parser.parse_args()

    ec2 = boto3.client("ec2")

    try:
        # Optional --create path; everything after it is the required listing
        # behavior of this script. -Deepseek
        if args.create:
            my_ip_cidr = args.my_ip
            if not my_ip_cidr:
                my_ip_cidr = get_public_ip_cidr()
                if not my_ip_cidr:
                    print(
                        "Could not auto-detect your public IP; "
                        "pass --my-ip 203.0.113.5/32."
                    )
                    return 1
                print(f"Detected public IP: {my_ip_cidr}")

            vpc_id = args.vpc_id or get_default_vpc_id(ec2)
            if not vpc_id:
                print("No default VPC found; pass --vpc-id to choose one.")
                return 1

            create_lab_groups(ec2, args.create, my_ip_cidr, vpc_id)
            return 0

        if args.security_group:
            security_group = describe_one_security_group(ec2, args.security_group)
            if security_group is None:
                print(f"Security group {args.security_group} was not found.")
                return 1
            security_groups = [security_group]
        else:
            security_groups = describe_all_security_groups(ec2)

        if not security_groups:
            print("No security groups were found in this account.")
            return 0

        print_report(security_groups)

    except ClientError as error:
        code = error.response["Error"]["Code"]
        operation = error.operation_name
        if code in DENIED_ERROR_CODES:
            print(f"Access denied: you are not allowed to call {operation}.")
            if args.create:
                print(
                    "This script needs ec2:CreateSecurityGroup, "
                    "ec2:AuthorizeSecurityGroupIngress and ec2:DescribeSecurityGroups."
                )
            else:
                print("This script needs ec2:DescribeSecurityGroups.")
            return 1
        print(f"EC2 error from {operation}: {code}: {error.response['Error'].get('Message')}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
