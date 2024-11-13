from flask_sock import Sock
import paramiko
from flask import current_app
from app.models import VM

sock = Sock()

@sock.route('/ws/vm/<int:vm_id>')
def vm_socket(ws, vm_id):
    vm = VM.query.get_or_404(vm_id)
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vm.ip_address, username=vm.username, password=vm.password)
        
        channel = ssh.invoke_shell()
        
        while True:
            if channel.recv_ready():
                data = channel.recv(1024).decode('utf-8')
                ws.send(data)
            
            try:
                data = ws.receive(timeout=0.1)
                if data:
                    channel.send(data)
            except:
                continue
                
    except Exception as e:
        ws.send(f"Error: {str(e)}\n")
    finally:
        if 'ssh' in locals():
            ssh.close() 