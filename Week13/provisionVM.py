# Import the needed credential and management objects from thelibraries.
from azure.identity import AzureCliCredential
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (AddressSpace,NetworkInterface,NetworkInterfaceIPConfiguration,PublicIPAddress,PublicIPAddressSku,Subnet,VirtualNetwork)
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (HardwareProfile,ImageReference,NetworkInterfaceReference,NetworkProfile,OSProfile,StorageProfile,VirtualMachine)
import os
import sys
# Acquire a credential object using CLI-based authentication.
credential = AzureCliCredential()
# Retrieve subscription ID from environment variable.
# NOTE: the env var NAME is AZURE_SUBSCRIPTION_ID; its VALUE is your subscription GUID.
# Set it once per shell (PowerShell): $env:AZURE_SUBSCRIPTION_ID="02cb372f-c8c5-4a0c-b9f4-574eeb4d6d38"
SUBSCRIPTION_ID_FALLBACK = "02cb372f-c8c5-4a0c-b9f4-574eeb4d6d38"
subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID") or SUBSCRIPTION_ID_FALLBACK
if not subscription_id:
    sys.exit("AZURE_SUBSCRIPTION_ID is not set. Set it to your subscription GUID before running.")
# Step 1: Retrieve your resource group fall2026-adv-scripting-<Your-Madison-College-Username>
#Setup the resource management client with our credential
resource_client = ResourceManagementClient(credential, subscription_id)
#Setup the Resource Group we are looking for and the region
RESOURCE_GROUP_NAME = "fall26-adv-scripting-KFRASIERVAN"
LOCATION = "eastus"
#Use the SDK to look up the resource groups using the list function
rgList = resource_client.resource_groups.list()
#Loop through each group in the list and print it. You may only see yours here.
print("Listing Resource Groups in this Subscription and Location...")
for group in list(rgList):
    print(f"{group.name}:{group.location}")
# Step 2: provision a virtual network
# A virtual machine requires a network interface client (NIC). A NICrequires
# a virtual network and subnet along with an IP address. Therefore we must provision
# these downstream components first, then provision the NIC, after which we
# can provision the VM.
# Network and IP address names
VNET_NAME = "python-example-vnet"
SUBNET_NAME = "python-example-subnet"
IP_NAME = "python-example-ip"
IP_CONFIG_NAME = "python-example-ip-config"
NIC_NAME = "python-example-nic"
# Obtain the management object for networks
network_client = NetworkManagementClient(credential, subscription_id)
# Provision the virtual network and wait for completion
poller = network_client.virtual_networks.begin_create_or_update(RESOURCE_GROUP_NAME,VNET_NAME,
    VirtualNetwork(
        location=LOCATION,
        address_space=AddressSpace(
            address_prefixes=["10.0.0.0/16"]
        )
    )
)
vnet_result = poller.result()
print(f"Provisioned virtual network {vnet_result.name} with address prefixes {vnet_result.address_space.address_prefixes}")
# Step 3: Provision the subnet and wait for completion
poller = network_client.subnets.begin_create_or_update(RESOURCE_GROUP_NAME, VNET_NAME, SUBNET_NAME,
    Subnet(address_prefix="10.0.0.0/24")
)
subnet_result = poller.result()
print(f"Provisioned virtual subnet {subnet_result.name} with address prefix {subnet_result.address_prefix}")
# Step 4: Provision an IP address and wait for completion
poller = network_client.public_ip_addresses.begin_create_or_update(RESOURCE_GROUP_NAME, IP_NAME,
    PublicIPAddress(
        location=LOCATION,
        sku=PublicIPAddressSku(name="Standard"),
        public_ip_allocation_method="Static",
        public_ip_address_version="IPv4"
    )
)
ip_address_result = poller.result()
print(f"Provisioned public IP address {ip_address_result.name} with address {ip_address_result.ip_address}")
# Step 5: Provision the network interface client
poller = network_client.network_interfaces.begin_create_or_update(RESOURCE_GROUP_NAME, NIC_NAME,
    NetworkInterface(
        location=LOCATION,
        ip_configurations=[NetworkInterfaceIPConfiguration(
            name=IP_CONFIG_NAME,
            subnet=Subnet(id=subnet_result.id),
            public_ip_address=PublicIPAddress(id=ip_address_result.id)
        )]
    )
)
nic_result = poller.result()
print(f"Provisioned network interface client {nic_result.name}")
# Step 6: Provision the virtual machine
# Obtain the management object for virtual machines
compute_client = ComputeManagementClient(credential, subscription_id)
VM_NAME = "KAIFV-VM"
USERNAME = "azureuser"
PASSWORD = "ChangePa$$w0rd24"
print(f"Provisioning virtual machine {VM_NAME}; this operation might take a few minutes.")
# Provision the VM specifying only minimal arguments, which defaults to an Ubuntu 24.04 VM
# on a Standard DS1 v2 plan with a public IP address and a default virtual network/subnet.
poller = compute_client.virtual_machines.begin_create_or_update(RESOURCE_GROUP_NAME, VM_NAME,
    VirtualMachine(
        location=LOCATION,
        storage_profile=StorageProfile(
            image_reference=ImageReference(
                publisher="Canonical",
                offer="ubuntu-24_04-lts",
                sku="server",
                version="latest"
            )
        ),
        hardware_profile=HardwareProfile(vm_size="Standard_DS1_v2"),
        os_profile=OSProfile(
            computer_name=VM_NAME,
            admin_username=USERNAME,
            admin_password=PASSWORD
        ),
        network_profile=NetworkProfile(
            network_interfaces=[NetworkInterfaceReference(id=nic_result.id)]
        )
    )
)
vm_result = poller.result()
print(f"Provisioned virtual machine {vm_result.name}")
