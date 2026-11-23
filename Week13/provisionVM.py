# Import the needed credential and management objects from thelibraries.
from azure.identity import AzureCliCredential
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.network.models import (AddressSpace,NetworkInterface,NetworkInterfaceIPConfiguration,PublicIPAddress,PublicIPAddressSku,Subnet,VirtualNetwork)
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.compute.models import (HardwareProfile,ImageReference,NetworkInterfaceReference,NetworkProfile,OSProfile,StorageProfile,VirtualMachine)
import os
# Acquire a credential object using CLI-based authentication.
credential = AzureCliCredential()
# Retrieve subscription ID from environment variable.
subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
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