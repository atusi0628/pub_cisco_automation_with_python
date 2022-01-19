from azure.identity import ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient
from netmiko import ConnectHandler
import ipaddress
import jinja2

# IOS information and credential
cisco_ios = {
        'device_type': 'cisco_ios',
        'host': '<Your management ip>',
        'username': '<Your username>',
        'password': '<Your password>',
        'port': 22
        }

# Credentials for Azure
SUBSCRIPTION_ID = "<Your subscription id>"
TENANT_ID = "<Your AAD tenant id>"
CLIENT_ID = "<Your app id obtain from service principal>"
SECRET = "<Your app secret obtain from service principal>"

# Information used to obtain the Azure IP ranges
location = "<Your Azure region>"
target_tag_name = "<Target service tag name>"


def main():
    # Connect to Azure
    credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, SECRET)
    network_client = NetworkManagementClient(credential, SUBSCRIPTION_ID)
    
    # Get IP ranges
    result = network_client.service_tags.list(location)

    for item in result.values:
        if item.name == target_tag_name:
            address_prefixes = item.properties.address_prefixes

    # Create lists used to generate config file
    ipv4_sequence = 10
    ipv6_sequence = 10
    ipv4_list = []
    ipv6_list = []

    for item in address_prefixes:
        address_object = ipaddress.ip_network(item)

        # Create list for IPv4 ACL config
        if address_object.version == 4:
            address = str(address_object.network_address)
            wildcard = str(address_object.hostmask)
            ipv4_list.append({'sequence':ipv4_sequence, 'address': address, 'wildcard': wildcard})
            ipv4_sequence += 1
        # Create list for IPv6 ACL config
        else:
            address_mask = str(address_object)
            ipv6_list.append({'sequence': ipv6_sequence, 'address_mask': address_mask})
            ipv6_sequence += 1

    # Generate config from ipv4_list
    with open('ios_acl_ipv4.conf', 'w') as f:
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('./templates/'))
        template = env.get_template('ios_acl_ipv4.j2')
        result = template.render(ipv4_list=ipv4_list)
        f.write(result)

    # Generate config from ipv6_list
    with open('ios_acl_ipv6.conf', 'w') as f:
        env = jinja2.Environment(loader=jinja2.FileSystemLoader('./templates/'))
        template = env.get_template('ios_acl_ipv6.j2')
        result = template.render(ipv6_list=ipv6_list)
        f.write(result)

    # Connect IOS
    ssh = ConnectHandler(**cisco_ios)
    ssh.enable()

    # Send config
    ssh.send_config_from_file('ios_acl_ipv4.conf')
    ssh.send_config_from_file('ios_acl_ipv6.conf')

    # Close connection
    ssh.disconnect()

if __name__ == '__main__':
    main()
