from functools import wraps
from flask import request, current_app, g
from flask_login import current_user
import requests
import paramiko
from app.models import VM, DynatraceEnvironment, AKSCluster
from app.courses import courses_bp

def section_route(endpoint, methods=['GET', 'POST']):
    """
    Decorator for section-specific routes.
    """
    def decorator(f):
        f._endpoint = endpoint
        f.methods = methods
        
        # Create a unique function name by prefixing with course and section info
        module_parts = f.__module__.split('.')
        course_name = module_parts[-4]  # e.g., '02-kubernetes-troubleshooting'
        section_name = module_parts[-2]  # e.g., '01-quickstart'
        
        # Create unique function name
        unique_func_name = f"{course_name}_{section_name}_{f.__name__}"
        f.__name__ = unique_func_name
        
        @wraps(f)
        def wrapped(course_id, section_id, *args, **kwargs):
            return f(course_id=course_id, section_id=section_id, *args, **kwargs)
        
        # Register the route with the blueprint using the unique function name
        url = f'/<course_id>/<section_id>/{endpoint}'
        unique_endpoint = f"section_{unique_func_name}_{endpoint}"
        
        courses_bp.add_url_rule(
            url,
            endpoint=unique_endpoint,
            view_func=wrapped,
            methods=methods
        )
        
        return wrapped
    return decorator


# Decorator for section initialization that I can use to run some code before the section is loaded
def section_init(init_id):
    """
    Decorator for section initialization functions.
    Must return a valid response or raise an exception to prevent section loading.
    """
    def decorator(f):
        f._init = True
        f._init_id = init_id
        
        @wraps(f)
        def wrapped(course_id, section_id, *args, **kwargs):
            try:
                result = f(course_id=course_id, section_id=section_id, *args, **kwargs)
                if not isinstance(result, dict) or 'valid' not in result:
                    raise ValueError("Init function must return dict with 'valid' key")
                return result
            except Exception as e:
                return {
                    'valid': False,
                    'message': str(e)
                }
        return wrapped
    return decorator


def make_dt_api_call_without_user_env(endpoint, token, method, params=None, **kwargs):
    """
    Make a call to Dynatrace API without using the current user's environment
    """
    # Build API URL
    try:
        api_url = endpoint
        
        # Add token to headers
        headers = kwargs.pop('headers', {})
        headers.update({
            'Authorization': f'Api-Token {token}',
            'Accept': 'application/json'
        })
        
        # Make request
        response = requests.request(
            method=method,
            url=api_url,
            params=params,
            headers=headers,
            **kwargs
        )
        
        # Raise for status
        response.raise_for_status()
        return response
        
    except Exception as e:
        current_app.logger.error(f"DT API call failed: {str(e)}")
        raise

# Function to call DT API with the current user's token
def dt_api_call(dt_env, endpoint,method='GET', params=None,  **kwargs):
    """
    Make a call to Dynatrace API using current user's environment and token
    
    Args:
        endpoint (str): API endpoint path
        method (str): HTTP method (GET, POST, etc.)
        **kwargs: Additional arguments to pass to requests
    
    Returns:
        requests.Response: API response
    
    Raises:
        Exception: If user has no Dynatrace environment configured
    """

    try:
        # Get user's Dynatrace environment
        dt_env = DynatraceEnvironment.query.filter_by(user_id=current_user.id).first()
        if not dt_env:
            raise Exception("No Dynatrace environment configured for user")

        # Build API URL
        api_url = f"{dt_env.environment_api_endpoint().rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Add token to headers
        headers = kwargs.pop('headers', {})
        headers.update({
            'Authorization': f'Api-Token {dt_env.environment_api_token}',
            'Accept': 'application/json'
        })
        
        # Make request
        response = requests.request(
            method=method,
            url=api_url,
            params=params,
            headers=headers,
            **kwargs
        )
        
        # Raise for status
        response.raise_for_status()
        return response
        
    except Exception as e:
        current_app.logger.error(f"DT API call failed: {str(e)}")
        raise

# Function to execute a command in the current user vm
def execute_command_in_vm(command, cluster_name=None, vm_id=None):
    """
    Execute a command in the user's VM
    
    Args:
        command (str): Command to execute
        cluster_name (str, optional): Name of the cluster to use
        vm_id (int, optional): Specific VM ID to use
    
    Returns:
        tuple: (stdout, stderr) from command execution
    
    Raises:
        Exception: If no VM is found or connection fails
    """
    try:
        # Get VM either by ID or from cluster
        vm = None
        if vm_id:
            vm = VM.query.get(vm_id)
            # Verify user has access to this VM
            if not current_user.is_admin:
                cluster = AKSCluster.query.filter_by(vm_id=vm_id, user_id=current_user.id).first()
                if not cluster:
                    raise Exception("Access denied to this VM")
        elif cluster_name:
            cluster = AKSCluster.query.filter_by(
                name=cluster_name,
                user_id=current_user.id
            ).first()
            if not cluster or not cluster.vm:
                raise Exception(f"No VM found for cluster {cluster_name}")
            vm = cluster.vm
        else:
            # Get the first cluster and VM for current user
            cluster = AKSCluster.query.filter_by(user_id=current_user.id).first()
            if not cluster or not cluster.vm:
                raise Exception("No VM found for user")
            vm = cluster.vm

        if not vm:
            raise Exception("VM not found")

        # Connect to VM
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        try:
            ssh.connect(
                hostname=vm.ip_address,
                username=vm.username,
                password=vm.password
            )
            
            # Execute command
            stdin, stdout, stderr = ssh.exec_command(command)
            
            # Read output
            stdout_str = stdout.read().decode()
            stderr_str = stderr.read().decode()
            
            return stdout_str, stderr_str
            
        finally:
            ssh.close()

    except Exception as e:
        current_app.logger.error(f"VM command execution failed: {str(e)}")
        raise


def re_deploy_operator():
    """
    Redeploys the Dynatrace operator for the current user's cluster using their VM.
    Makes a request to the deploy-dynakube endpoint with the current user's configuration.
    
    Returns:
        tuple: (success, message) indicating deployment status
    """
    try:
        # Get user's Dynatrace environment
        dt_env = DynatraceEnvironment.query.filter_by(user_id=current_user.id).first()
        if not dt_env:
            raise Exception("No Dynatrace environment configured for user")

        # Get the user's cluster and VM
        cluster = AKSCluster.query.filter_by(user_id=current_user.id).first()
        if not cluster or not cluster.vm:
            raise Exception("No cluster or VM found for user")

        # Prepare the dynakube YAML content
        dynakube_yaml = f"""apiVersion: dynatrace.com/v1beta1
kind: DynaKube
metadata:
  name: dynakube
  namespace: dynatrace
spec:
  apiUrl: {dt_env.environment_url}
  oneAgent:
    classicFullStack:
      tolerations:
      - effect: NoSchedule
        key: node-role.kubernetes.io/master
        operator: Exists
      - effect: NoSchedule
        key: node-role.kubernetes.io/control-plane
        operator: Exists
  activeGate:
    capabilities:
      - routing
      - kubernetes-monitoring
    group: training"""

        # Make request to deploy-dynakube endpoint
        response = requests.post(
            f"{request.url_root.rstrip('/')}/admin/api/deploy-dynakube",
            json={
                'yaml_content': dynakube_yaml,
                'vm_id': cluster.vm.id,
                'cluster_name': cluster.name
            },
            headers={'Content-Type': 'application/json'},
            cookies=request.cookies  # Pass current session cookies
        )

        if not response.ok:
            raise Exception(f"Deploy request failed: {response.text}")

        result = response.json()
        if not result.get('success'):
            raise Exception(result.get('message', 'Unknown error during deployment'))

        return True, "Dynatrace operator redeployed successfully"

    except Exception as e:
        current_app.logger.error(f"Failed to redeploy operator: {str(e)}")
        return False, str(e)