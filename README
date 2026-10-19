This is a minimally-operational prototype of an HTML5/WebRTC transceiver for ASL3. I am undecided about whether to complete the work to turn it into a usable transceiver to replace the old Java Web Transceiver. Its present purpose is solely to serve as a demonstration integration for Call Sign Connect, rather than to be generally useful.

# Preparation
1. Choose an FQDN for your server and sort out any DNS registration formalities.
2. Register your [server](https://allstarlink.org/portal/servers.php) and (if required) a new [node](https://allstarlink.org/portal/nodes.php) at allstarlink.org

# AWS setup
3. Allocate an [Elastic IP Address](https://console.aws.amazon.com/ec2/home#Addresses:) for your server.
 * You might find it useful to include a Name tag with the FQDN as its value.
4. Create a DNS A record mapping the FQDN to the EIP address
5. Determine your unqualified hostname. This is simply the first label of the server's FQDN. For mydomain.example that means "mydomain". For service.mydomain.example that means "service".
6. In [SSM Parameter Store](https://console.aws.amazon.com/systems-manager/parameters/) create the following parameters, substituting your unqualified hostname in each case:
 - /{hostname}/asl_node_number
  * Per allstarlink.org
 - /{hostname}/asl_node_password
  * Per allstarlink.org
 - /{hostname}/certbot_args
  * --agree-tos, assuming that you do indeed accept Let's Encrypt's ToS
 - /{hostname}/domain_name
  * The FQDN
 - /{hostname}/eip_address
  * As allocated above
 - /{hostname}/email_address
  * For notices from Let's Encrypt. --no-eff-email is asserted in the playbook, so this is not expected to sign you up for the marketing material.
 - /{hostname}/ssh_public_key
  * The exact contents of ~/.ssh/{something}.pub that you wish to use to access the server
7. In [CloudFormation](https://console.aws.amazon.com/cloudformation/home#/stacks?filteringText=&filteringStatus=active&viewNested=true)
 1. Create Stack > With new resources (standard)
 2. Upload a template file
 3. Choose file
 4. csc-asl3/CloudFormation/template.yaml
 5. Next
 6. Stack name: {unqualified host name, as above}
 7. Next
 8. Tick "I acknowledge that AWS CloudFormation might create IAM resources."
  * It really will. See ASLInstanceRole in template.yaml for details. At present it's limited to fetching SSM parameters with a /{hostname}/ prefix, like those created above.
 9. Next
 10. Submit
 11. Wait a few minutes for it to complete

# Install and test the software
8. Deploy the software: bin/deploy {fqdn}
9. Install the placeholder password
 * The need for this will disappear once CSC integration is complete. Even in its current state the system has access to real, licensed transmitters, so some access control is warranted.
 1. ssh admin@{fqdn}
 2. sudo -s
 3. cat /run/www-data/secret/csc-placeholder.json
  * Note that this disappears at reboot, so you'll need to redo this when/if you reboot.
 4. Open the transceiver at https://{fqdn}/h5t
  * Only tested in Chrome at present. There's some WebRTC problem with Firefox that I've not been able to resolve yet :-(
 5. F12 to open the developer tools
 6. Console
 7. localStorage.setItem('csc-placeholder', '{password}')
  * Obviously use the actual placeholder password obtained in the previous step
10. Test the transceiver with a public parrot
 1. Type in the node number that you configured above
 2. Press Connect
  * If all is well, the red DISCONNECTED label at the top right will be replaced with a green CONNECTED label
  * Watching the dashboard at https://{fqdn}/allmon3/ is probably helpful to work out what's happening
 3. Enter *355553 and Send DTMF Code
  * If all is well you'll see the connect on Allmon3 and hear a message from the parrot at 55553
 4. Talk to the parrot
  * There is a real need to add buffering; you'll probably need to hold PTT for a couple of seconds before and after you speak
 5. Enter *155553 and Send DTMF Code
  * If all is well you'll disconnect from the parrot

