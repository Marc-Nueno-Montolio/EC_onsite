import paramiko
from app.models import VM
from app import db
import subprocess

def execute_vm_command(vm_id, command):
    """
    Execute a command on a VM and return its output
    
    Args:
        vm_id: The ID of the VM to connect to
        command: The command to execute
        
    Returns:
        tuple: (success, output/error_message)
    """
    vm = VM.query.get(vm_id)
    if not vm:
        return False, "VM not found"
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        ssh.connect(
            hostname=vm.ip_address,
            username=vm.username,
            password=vm.password,
            timeout=10
        )
        
        stdin, stdout, stderr = ssh.exec_command(command)
        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')
        
        ssh.close()
        
        if error:
            return False, error
        return True, output
        
    except Exception as e:
        return False, str(e) 

def copy_to_vm(vm_id, source_path, dest_path):
    try:
        vm = VM.query.get(vm_id)
        if not vm:
            return False
            
        scp_command = f'scp {source_path} {vm.username}@{vm.ip}:{dest_path}'
        result = subprocess.run(scp_command, shell=True, capture_output=True, text=True)
        
        return result.returncode == 0
    except Exception as e:
        print(f"Error copying file to VM: {str(e)}")
        return False 