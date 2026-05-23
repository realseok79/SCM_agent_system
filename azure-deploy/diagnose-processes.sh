#!/usr/bin/expect -f
set timeout 15
spawn ssh -o StrictHostKeyChecking=no azureuser@20.41.110.255
expect "password:"
send "Scm_Secure_Password_2026!\r"
expect "azureuser@"

send "echo '=========================================' && echo '🔍 ACTIVE SYSTEM PROCESSES' && echo '========================================='\r"
expect "azureuser@"

# List active processes with complete command lines
send "ps aux | grep -iE \"(docker|compose|build|tar|gradle|java|pip|apt)\" | grep -v grep\r"
expect "azureuser@"

send "exit\r"
expect eof
