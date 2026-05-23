#!/usr/bin/expect -f

# Set connection timeout
set timeout 15

# Connect via SSH
spawn ssh -o StrictHostKeyChecking=no azureuser@20.41.110.255

# Handle password prompt
expect {
    "password:" {
        send "Scm_Secure_Password_2026!\r"
    }
    timeout {
        send_user "\n❌ SSH connection timed out.\n"
        exit 1
    }
}

# Wait for shell prompt
expect {
    "azureuser@" {
        # Successfully logged in!
    }
    timeout {
        send_user "\n❌ Login failed or prompt not found.\n"
        exit 1
    }
}

# Run diagnostics
send "echo '=========================================' && echo '📊 REMOTE VM DIAGNOSTIC REPORT' && echo '========================================='\r"
expect "azureuser@"

# 1. CPU & Memory Load
send "echo '--- 💻 CPU & MEMORY LOAD ---' && top -b -n 1 | head -n 15\r"
expect "azureuser@"

# 2. Disk Space
send "echo '--- 💾 DISK SPACE ---' && df -h /\r"
expect "azureuser@"

# 3. Docker status
send "echo '--- 🐳 DOCKER CONTAINERS ---' && docker ps -a\r"
expect "azureuser@"

# Exit SSH
send "exit\r"
expect eof
