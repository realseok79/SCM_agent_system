#!/usr/bin/expect -f
set timeout 60
spawn ssh -o StrictHostKeyChecking=no azureuser@20.41.110.255
expect "password:"
send "Scm_Secure_Password_2026!\r"
expect "azureuser@"

send "cd /home/azureuser/scm-agent-deploy\r"
expect "azureuser@"

send "docker-compose logs --tail=25 backend\r"
expect "azureuser@"

send "exit\r"
expect eof
