from flask import render_template, redirect, url_for, flash, request, jsonify, current_app, abort, send_file
from flask_login import login_required, current_user
from app.admin import admin_bp
from app.models import User, DynatraceEnvironment, VM, AKSCluster, Deployment
from app.forms import DynatraceEnvironmentForm, UserForm, VMForm, AKSClusterForm
from app import db
from app import socketio  # Add this import at the top with other imports
import tempfile, subprocess

from app.models import SectionCompletion
from app.courses.routes import get_courses
from app.utils.vm_commands import execute_vm_command, copy_to_vm
from flask import current_app
from threading import Thread
from app import socketio
import os
import yaml
import traceback
import paramiko
from flask_socketio import emit
from app.utils.script_handler import ScriptRunner

import threading  # Add this import at the top
from app.scripts.log_generator import run as log_generator_run
from app.scripts.log_generator_parse_examples import run as log_generator_parse_examples_run

import json
from datetime import datetime
import time

from werkzeug.utils import secure_filename
from jinja2 import Template

script_runner = ScriptRunner(socketio)

@admin_bp.route('/')
@login_required
def admin_dashboard():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/new', methods=['GET', 'POST'])
@login_required
def create_user():
    form = UserForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, is_admin=form.is_admin.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('User created successfully')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/user_form.html', form=form, title='Create User')

@admin_bp.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    if form.validate_on_submit():
        user.username = form.username.data
        user.is_admin = form.is_admin.data
        if form.password.data:
            user.set_password(form.password.data)
        db.session.commit()
        flash('User updated successfully')
        return redirect(url_for('admin.admin_dashboard'))
    return render_template('admin/user_form.html', form=form, title='Edit User')

@admin_bp.route('/user-progress')
@login_required
def user_progress():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
        
    users = User.query.all()
    courses = get_courses()
    users_progress = {}
    
    for user in users:
        completions = SectionCompletion.query.filter_by(user_id=user.id).all()
        completion_map = {(c.course_id, c.section_id) for c in completions}
        users_progress[user.id] = {
            'user': user,
            'courses': {}
        }
        
        for course in courses:
            course_id = course['id']
            completed_sections = [
                section for section in course['sections'] 
                if (course_id, section) in completion_map
            ]
            
            users_progress[user.id]['courses'][course_id] = {
                'title': course['title'],
                'all_sections': course['sections'],
                'completed': completed_sections,
                'completion_percentage': round(len(completed_sections) / len(course['sections']) * 100)
            }
    
    return render_template('admin/admin_progress.html', 
                         users_progress=users_progress,
                         courses=courses)

@admin_bp.route('/toggle-completion', methods=['POST'])
@login_required
def toggle_completion():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
        
    data = request.json
    user_id = data.get('user_id')
    course_id = data.get('course_id')
    section_id = data.get('section_id')
    
    try:
        completion = SectionCompletion.query.filter_by(
            user_id=user_id,
            course_id=course_id,
            section_id=section_id
        ).first()
        
        if completion:
            db.session.delete(completion)
            action = 'unmarked'
        else:
            completion = SectionCompletion(
                user_id=user_id,
                course_id=course_id,
                section_id=section_id
            )
            db.session.add(completion)
            action = 'marked'
            
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': f'Section {action} as complete'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@admin_bp.route('/dynatrace-environments')
@login_required
def list_dynatrace_environments():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    environments = DynatraceEnvironment.query.all()
    return render_template('admin/dynatrace_environments.html', environments=environments)

@admin_bp.route('/dynatrace-environments/new', methods=['GET', 'POST'])
@login_required
def create_dynatrace_environment():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    form = DynatraceEnvironmentForm()
    if form.validate_on_submit():
        environment = DynatraceEnvironment(
            environment_name=form.environment_name.data,
            environment_id=form.environment_id.data,
            environment_url=form.environment_url.data,
            environment_api_token=form.environment_api_token.data,
            environment_paas_token=form.environment_paas_token.data,
            user_id=form.user_id.data  # Link to the selected user
        )
        db.session.add(environment)
        db.session.commit()
        flash('Dynatrace environment created successfully', 'success')
        return redirect(url_for('admin.list_dynatrace_environments'))
    
    return render_template('admin/dynatrace_environment_form.html', form=form, title='Create Dynatrace Environment')

@admin_bp.route('/dynatrace-environments/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_dynatrace_environment(id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    environment = DynatraceEnvironment.query.get_or_404(id)
    form = DynatraceEnvironmentForm(obj=environment)
    
    if form.validate_on_submit():
        environment.environment_name = form.environment_name.data
        environment.environment_id = form.environment_id.data
        environment.environment_url = form.environment_url.data
        environment.environment_api_token = form.environment_api_token.data
        environment.environment_paas_token = form.environment_paas_token.data
        environment.is_managed = form.is_managed.data
        environment.user_id = form.user_id.data
        db.session.commit()
        flash('Dynatrace environment updated successfully', 'success')
        return redirect(url_for('admin.list_dynatrace_environments'))
    
    return render_template('admin/dynatrace_environment_form.html', form=form, title='Edit Dynatrace Environment')

@admin_bp.route('/dynatrace-environments/<int:id>/delete', methods=['POST'])
@login_required
def delete_dynatrace_environment(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    environment = DynatraceEnvironment.query.get_or_404(id)
    db.session.delete(environment)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Dynatrace environment deleted successfully'})

@admin_bp.route('/vms')
@login_required
def list_vms():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    vms = VM.query.all()
    return render_template('admin/vms.html', vms=vms)

@admin_bp.route('/vms/new', methods=['GET', 'POST'])
@login_required
def create_vm():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
        
    form = VMForm()
    form.user_id.choices = [(u.id, u.username) for u in User.query.all()]
    
    if form.validate_on_submit():
        vm = VM(
            name=form.name.data,
            ip_address=form.ip_address.data,
            username=form.username.data,
            password=form.password.data,
            user_id=form.user_id.data
        )
        db.session.add(vm)
        db.session.commit()
        flash('VM created successfully')
        return redirect(url_for('admin.list_vms'))
        
    return render_template('admin/vm_form.html', form=form, title='Create VM')

@admin_bp.route('/vms/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_vm(id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    vm = VM.query.get_or_404(id)
    form = VMForm(obj=vm)
    
    if form.validate_on_submit():
        vm.name = form.name.data
        vm.ip_address = form.ip_address.data
        vm.username = form.username.data
        if form.password.data:  # Only update password if provided
            vm.password = form.password.data
        vm.user_id = form.user_id.data
        db.session.commit()
        flash('VM updated successfully')
        return redirect(url_for('admin.list_vms'))
        
    return render_template('admin/vm_form.html', form=form, title='Edit VM')

@admin_bp.route('/vms/<int:id>/delete', methods=['POST'])
@login_required
def delete_vm(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    vm = VM.query.get_or_404(id)
    db.session.delete(vm)
    db.session.commit()
    return jsonify({'success': True, 'message': 'VM deleted successfully'})

@admin_bp.route('/vms/<int:id>/console')
@login_required
def vm_console(id):
    # Check that user owns the vm or is admin, otherwise, redirect to main.index
    vm = VM.query.get_or_404(id)
    if not current_user.is_admin and vm.user_id != current_user.id:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    return render_template('admin/vm_console.html', vm=vm)

@admin_bp.route('/aks-clusters')
@login_required
def list_aks_clusters():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    clusters = AKSCluster.query.all()
    # Add related data for display
    for cluster in clusters:
        cluster.user = User.query.get(cluster.user_id)
        cluster.vm = VM.query.get(cluster.vm_id) if cluster.vm_id else None
    return render_template('admin/aks_clusters.html', clusters=clusters)

@admin_bp.route('/aks-clusters/create', methods=['GET', 'POST'])
@login_required
def create_aks_cluster():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    form = AKSClusterForm()
    if form.validate_on_submit():
        cluster = AKSCluster(
            name=form.name.data,
            subscription_id=form.subscription_id.data,
            azure_id=form.azure_id.data,
            user_id=form.user_id.data,
            vm_id=form.vm_id.data if form.vm_id.data != 0 else None
        )
        db.session.add(cluster)
        db.session.commit()
        flash('AKS Cluster created successfully')
        return redirect(url_for('admin.list_aks_clusters'))
        
    return render_template('admin/aks_cluster_form.html', form=form, title='Create AKS Cluster')

@admin_bp.route('/aks-clusters/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_aks_cluster(id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    cluster = AKSCluster.query.get_or_404(id)
    form = AKSClusterForm(obj=cluster)
    
    if form.validate_on_submit():
        cluster.name = form.name.data
        cluster.subscription_id = form.subscription_id.data
        cluster.azure_id = form.azure_id.data
        cluster.user_id = form.user_id.data
        cluster.vm_id = form.vm_id.data if form.vm_id.data != 0 else None
        
        db.session.commit()
        flash('AKS Cluster updated successfully')
        return redirect(url_for('admin.list_aks_clusters'))
        
    return render_template('admin/aks_cluster_form.html', form=form, title='Edit AKS Cluster')

@admin_bp.route('/aks-clusters/<int:id>/delete', methods=['POST'])
@login_required
def delete_aks_cluster(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    cluster = AKSCluster.query.get_or_404(id)
    db.session.delete(cluster)
    db.session.commit()
    return jsonify({'success': True, 'message': 'AKS Cluster deleted successfully'})

@admin_bp.route('/aks-clusters/<int:cluster_id>/kubectl')
@login_required
def launch_kubectl(cluster_id):
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    cluster = AKSCluster.query.get_or_404(cluster_id)
    
    if not cluster.vm:
        flash('No VM associated with this cluster', 'error')
        return redirect(url_for('admin.list_aks_clusters'))
    
    # Redirect to VM console with kubectl check
    return redirect(url_for('admin.vm_console', id=cluster.vm.id, check_kubectl=True))

@admin_bp.route('/api/vm/<int:vm_id>/execute', methods=['POST'])
@login_required
def execute_command(vm_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
    
    command = request.json.get('command')
    if not command:
        return jsonify({'success': False, 'message': 'No command provided'}), 400
        
    success, output = execute_vm_command(vm_id, command)
    return jsonify({
        'success': success,
        'output': output
    })

@admin_bp.route('/api/execute-script', methods=['POST'])
@login_required
def execute_script():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'}), 403
        
    script_id = request.json.get('scriptId')
    scripts = {
        '1': {
            'name': 'Generate Application Logs',
            'description': 'Creates synthetic application logs on VM',
            'type': 'vm_script',
            'location': '/opt/scripts/generate_app_logs.sh',
            'vm_id': 1
        },
        '2': {
            'name': 'Local Log Generator',
            'description': 'Generates logs using Flask backend',
            'type': 'flask_script',
            'code': '''
import random
import time
log_levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
messages = ['User login', 'Database query', 'API request', 'Cache update']
return f"{random.choice(log_levels)}: {random.choice(messages)} at {time.time()}"
            '''
        },
        '3': {
            'name': 'Network Traffic Generator',
            'description': 'Generates synthetic network traffic on VM',
            'type': 'vm_script',
            'location': '/opt/scripts/network_traffic.sh',
            'vm_id': 2
        }
    }
    
    script = scripts.get(str(script_id))
    if not script:
        return jsonify({'success': False, 'message': 'Invalid script ID'})
    
    if script['type'] == 'vm_script':
        success, output = execute_vm_command(script['vm_id'], f"bash {script['location']}")
    else:  # flask_script
        try:
            # Execute the Python code block
            local_vars = {}
            exec(script['code'], globals(), local_vars)
            output = local_vars.get('output', 'Script executed successfully')
            success = True
        except Exception as e:
            success = False
            output = str(e)
    
    return jsonify({
        'success': success,
        'output': output
    })


@admin_bp.route('/api/deploy-dynakube', methods=['POST'])
@login_required
def deploy_dynakube():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})

    data = request.get_json()
    yaml_content = data.get('yaml_content')
    vm_id = data.get('vm_id')
    cluster_name = data.get('cluster_name')
    
    steps = []
    
    if not all([yaml_content, vm_id, cluster_name]):
        return jsonify({
            'success': False,
            'message': 'Missing required parameters'
        })
    
    try:
        # Get VM
        vm = VM.query.get(vm_id)
        if not vm:
            return jsonify({
                'success': False,
                'message': 'VM not found'
            })

        # Get AKS cluster and its associated user
        aks_cluster = AKSCluster.query.filter_by(name=cluster_name).first()
        if not aks_cluster:
            return jsonify({
                'success': False,
                'message': 'AKS Cluster not found'
            })
        
        # Debug logging
        current_app.logger.info(f"Cluster user_id: {aks_cluster.user_id}")
        
        # Get the Dynatrace environment for the cluster's user
        dt_environment = DynatraceEnvironment.query.filter_by(user_id=aks_cluster.user_id).first()
        
        # Debug logging
        if dt_environment:
            current_app.logger.info(f"Found DT environment: {dt_environment.environment_name}")
        else:
            # List all environments for debugging
            all_envs = DynatraceEnvironment.query.all()
            current_app.logger.info(f"All DT environments: {[(env.user_id, env.environment_name) for env in all_envs]}")
            return jsonify({
                'success': False,
                'message': f'No Dynatrace environment found for user {aks_cluster.user_id}'
            })

        # Rest of your deployment code...
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=vm.ip_address,
            username=vm.username,
            password=vm.password
        )

        # Create directory
        steps.append({'command': 'mkdir -p ~/dynatrace'})
        stdin, stdout, stderr = ssh.exec_command('mkdir -p ~/dynatrace')
        mkdir_output = stdout.read().decode()
        mkdir_error = stderr.read().decode()
        if mkdir_error:
            return jsonify({
                'success': False,
                'message': 'Failed to create directory',
                'details': mkdir_error
            })
        steps.append({'output': 'Directory created successfully'})

        # Copy operator YAML
        operator_source = os.path.join(current_app.root_path, 'scripts', 'deployment', 'operator.yaml')
        operator_dest = f'/home/{vm.username}/dynatrace/operator.yaml'
        sftp = ssh.open_sftp()
        sftp.put(operator_source, operator_dest)
        steps.append({'output': 'Operator YAML copied successfully'})

        # Cleanup: Delete existing operator if found
        steps.append({'command': f'kubectl delete -f {operator_dest} --ignore-not-found=true'})
        stdin, stdout, stderr = ssh.exec_command(f'kubectl delete -f {operator_dest} --ignore-not-found=true')
        cleanup_output = stdout.read().decode()
        cleanup_error = stderr.read().decode()
        if cleanup_output:
            steps.append({'output': 'Existing operator resources cleaned up'})

        # Cleanup: Delete existing secrets
        steps.append({'command': 'kubectl delete secret -n dynatrace dynakube --ignore-not-found=true'})
        stdin, stdout, stderr = ssh.exec_command('kubectl delete secret -n dynatrace dynakube --ignore-not-found=true')
        secret_cleanup_output = stdout.read().decode()
        secret_cleanup_error = stderr.read().decode()
        if secret_cleanup_output:
            steps.append({'output': 'Existing Dynatrace secrets cleaned up'})

        # Save Dynakube YAML
        dynakube_path = f'/home/{vm.username}/dynatrace/dynakube.yaml'
        with sftp.open(dynakube_path, 'w') as f:
            f.write(yaml_content)
        sftp.close()
        steps.append({'output': 'Dynakube YAML saved successfully'})

        # Create namespace
        steps.append({'command': 'kubectl create namespace dynatrace --dry-run=client -o yaml | kubectl apply -f -'})
        stdin, stdout, stderr = ssh.exec_command('kubectl create namespace dynatrace --dry-run=client -o yaml | kubectl apply -f -')
        namespace_output = stdout.read().decode()
        namespace_error = stderr.read().decode()
        if namespace_error and "already exists" not in namespace_error:
            return jsonify({
                'success': False,
                'message': 'Failed to create namespace',
                'details': namespace_error
            })
        steps.append({'output': namespace_output or 'Namespace created successfully'})

        # Apply operator
        steps.append({'command': f'kubectl apply -f {operator_dest}'})
        stdin, stdout, stderr = ssh.exec_command(f'kubectl apply -f {operator_dest}')
        operator_output = stdout.read().decode()
        operator_error = stderr.read().decode()
        if operator_error and "already exists" not in operator_error:
            return jsonify({
                'success': False,
                'message': 'Failed to apply operator',
                'details': operator_error
            })
        steps.append({'output': operator_output or 'Operator applied successfully'})

        # Wait for operator
        wait_command = 'kubectl -n dynatrace wait pod --for=condition=ready --selector=app.kubernetes.io/name=dynatrace-operator,app.kubernetes.io/component=webhook --timeout=300s'
        steps.append({'command': wait_command})
        stdin, stdout, stderr = ssh.exec_command(wait_command)
        wait_output = stdout.read().decode()
        wait_error = stderr.read().decode()
        steps.append({'output': wait_output or 'Operator is ready'})

        # Create secrets using the cluster owner's Dynatrace environment
        api_token = dt_environment.environment_paas_token
        steps.append({'command': f'kubectl -n dynatrace create secret generic dynakube --from-literal="apiToken={api_token}"'})
        stdin, stdout, stderr = ssh.exec_command(f'kubectl -n dynatrace create secret generic dynakube --from-literal="apiToken={api_token}"')
        secrets_output = stdout.read().decode()
        secrets_error = stderr.read().decode()
        steps.append({'output': secrets_output or 'Secrets created successfully'})

        # Apply Dynakube config
        steps.append({'command': f'kubectl apply -f {dynakube_path} -n dynatrace'})
        stdin, stdout, stderr = ssh.exec_command(f'kubectl apply -f {dynakube_path} -n dynatrace')
        kubectl_output = stdout.read().decode()
        kubectl_error = stderr.read().decode()
        if kubectl_error and "already exists" not in kubectl_error:
            return jsonify({
                'success': False,
                'message': 'Failed to apply Dynakube configuration',
                'details': kubectl_error
            })
        steps.append({'output': kubectl_output or 'Dynakube configuration applied successfully'})

        return jsonify({
            'success': True,
            'steps': steps
        })

    except Exception as e:
        current_app.logger.error(f"Error deploying Dynatrace: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        })

    finally:
        if 'ssh' in locals():
            ssh.close()

@admin_bp.route('/api/deploy-easytrade', methods=['POST'])
@login_required
def deploy_easytrade():
    data = request.get_json()
    cluster_id = data.get('cluster_id')
    vm_id = data.get('vm_id')
    cluster_name = data.get('cluster_name')
    
    if not all([cluster_id, vm_id, cluster_name]):
        return jsonify({
            'success': False,
            'message': 'Missing required parameters'
        })
    
    try:
        # Get the VM and cluster details
        vm = VM.query.get(vm_id)
        cluster = AKSCluster.query.get(cluster_id)
        if not vm or not cluster:
            raise Exception("VM or Cluster not found")

        # Setup SSH client
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(vm.ip_address, username=vm.username, password=vm.password)

        # Create directory if it doesn't exist
        stdin, stdout, stderr = ssh.exec_command('mkdir -p ~/easytrade')
        if stderr.read():
            mkdir_output = "Directory already exists"
        else:
            mkdir_output = "Directory created successfully"

        # Check if repository already exists
        stdin, stdout, stderr = ssh.exec_command('test -d ~/easytrade/.git && echo "exists"')
        repo_exists = stdout.read().decode().strip() == "exists"

        # Clone or pull repository
        if repo_exists:
            stdin, stdout, stderr = ssh.exec_command('cd ~/easytrade && git pull')
            git_output = "Repository updated successfully"
        else:
            stdin, stdout, stderr = ssh.exec_command('cd ~/easytrade && git clone https://github.com/Dynatrace/easytrade .')
            git_output = "Repository cloned successfully"

        # Create namespace (ignore if exists)
        stdin, stdout, stderr = ssh.exec_command('kubectl create namespace easytrade')
        namespace_output = stdout.read().decode() or "Namespace already exists"

        # Apply kubernetes manifests
        stdin, stdout, stderr = ssh.exec_command('cd ~/easytrade && kubectl apply -f kubernetes-manifests -n easytrade')
        kubectl_output = stdout.read().decode()
        kubectl_error = stderr.read().decode()

        if kubectl_error and 'error' in kubectl_error.lower():
            raise Exception(f"kubectl apply failed: {kubectl_error}")

        # Wait for the frontend service to get an external IP (max 5 minutes)
        max_attempts = 30  # 30 attempts * 10 seconds = 5 minutes
        frontend_ip = None
        frontend_port = None
        
        for attempt in range(max_attempts):
            stdin, stdout, stderr = ssh.exec_command(
                'kubectl get service frontendreverseproxy-easytrade -n easytrade -o json'
            )
            service_output = stdout.read().decode()
            service_error = stderr.read().decode()

            if service_error:
                current_app.logger.warning(f"Attempt {attempt + 1}: {service_error}")
                time.sleep(10)
                continue

            try:
                service_data = json.loads(service_output)
                if service_data.get('status', {}).get('loadBalancer', {}).get('ingress'):
                    frontend_ip = service_data['status']['loadBalancer']['ingress'][0].get('ip')
                    if frontend_ip:
                        frontend_port = service_data['spec']['ports'][0].get('port', 80)
                        current_app.logger.info(f"Found frontend IP: {frontend_ip}")
                        break
            except json.JSONDecodeError:
                pass

            current_app.logger.info(f"Attempt {attempt + 1}: Waiting for frontend IP...")
            time.sleep(10)

        if not frontend_ip:
            raise Exception("Timeout waiting for frontend service IP")

        # Update or create deployment record
        deployment = Deployment.query.filter_by(cluster_id=cluster_id).first()
        if not deployment:
            deployment = Deployment(cluster_id=cluster_id)

        deployment.frontend_ip = frontend_ip
        deployment.frontend_port = frontend_port
        deployment.last_updated = datetime.utcnow()

        db.session.add(deployment)
        db.session.commit()

        return jsonify({
            'success': True,
            'mkdir_output': mkdir_output,
            'git_output': git_output,
            'namespace_output': namespace_output,
            'kubectl_output': kubectl_output,
            'deployment': {
                'frontend_ip': frontend_ip,
                'frontend_port': frontend_port
            }
        })

    except Exception as e:
        current_app.logger.error(f"Deployment error: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e),
            'details': getattr(e, 'stderr', 'No additional details available')
        })
    
    finally:
        if 'ssh' in locals():
            ssh.close()

# Dictionary to track running scripts and their stop events
script_processes = {}
script_stop_events = {}

@admin_bp.route('/actions')
@login_required
def actions():
    scripts = {
        'log_gen': {
            'name': 'Basic Log Generator',
            'script_type': 'flask_script',
            'script_name': 'log_generator'
        },
        'log_gen_parse_examples': {
            'name': 'Log Generator Parse Examples',
            'description': 'Generates random log entries with different parsing examples',
            'script_type': 'flask_script',
            'script_name': 'log_generator_parse_examples'
        }
    }
    
    # Get all AKS clusters with their related VMs
    aks_clusters = AKSCluster.query.all()
    
    return render_template('admin/actions.html', 
                         scripts=scripts,
                         aks_clusters=aks_clusters)

@socketio.on('start_script')
def handle_start_script(data):
    script_id = data.get('script_id')
    script_name = data.get('script_name')
    
    if script_id in script_processes and script_processes[script_id].is_alive():
        socketio.emit('script_status', {
            'script_id': script_id,
            'status': 'already_running',
            'message': 'Script is already running'
        })
        return
    
    # Import the appropriate run function based on script_name
    script_map = {
        'log_generator': log_generator_run,
        'log_generator_parse_examples': log_generator_parse_examples_run,
    }
    
    if script_name in script_map:
        stop_event = threading.Event()
        thread = threading.Thread(target=script_map[script_name], args=(stop_event, current_app._get_current_object(), socketio))
        thread.daemon = True
        script_processes[script_id] = thread
        script_stop_events[script_id] = stop_event
        thread.start()

        
        socketio.emit('script_status', {
            'script_id': script_id,
            'status': 'active'
        })

@socketio.on('stop_script')
def handle_stop_script(data):
    script_id = data.get('script_id')
    if script_id in script_stop_events:
        script_stop_events[script_id].set()  # Signal the thread to stop
        script_processes.pop(script_id, None)
        script_stop_events.pop(script_id, None)
        
        # Emit status update
        socketio.emit('script_status', {
            'script_id': script_id,
            'status': 'inactive'
        })

@admin_bp.route('/deployments')
@login_required
def list_deployments():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    deployments = Deployment.query.all()
    return render_template('admin/deployments.html', deployments=deployments)

@admin_bp.route('/deployments/<int:id>/delete', methods=['POST'])
@login_required
def delete_deployment(id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    deployment = Deployment.query.get_or_404(id)
    try:
        db.session.delete(deployment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

COURSE_CONTENT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'courses')

@admin_bp.route('/file-explorer')
@login_required
def file_explorer():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('main.index'))
    
    path = request.args.get('path', '')
    base_path = COURSE_CONTENT_PATH
    current_path = os.path.join(base_path, path)
    
    # Security check to prevent directory traversal
    if not os.path.commonpath([current_path, base_path]) == base_path:
        flash('Invalid path', 'error')
        return redirect(url_for('admin.file_explorer'))
    
    # Files to exclude
    excluded_files = {'__init__.py', 'routes.py', 'utils.py'}
    
    files = []
    folders = []
    
    for item in os.listdir(current_path):
        # Skip excluded files in root directory
        if path == '' and item in excluded_files:
            continue
            
        item_path = os.path.join(current_path, item)
        relative_path = os.path.relpath(item_path, base_path)
        
        if os.path.isfile(item_path):
            # Get file extension
            _, ext = os.path.splitext(item.lower())
            # Determine if it's an image
            is_image = ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            
            files.append({
                'name': item,
                'path': relative_path,
                'size': os.path.getsize(item_path),
                'modified': os.path.getmtime(item_path),
                'modified_str': datetime.fromtimestamp(os.path.getmtime(item_path)).strftime('%Y-%m-%d %H:%M:%S'),
                'is_image': is_image,
                'extension': ext[1:] if ext else ''  # Remove the dot from extension
            })
        else:
            folders.append({
                'name': item,
                'path': relative_path
            })
    
    return render_template('admin/file_explorer.html', 
                         files=files, 
                         folders=folders, 
                         current_path=path)

@admin_bp.route('/file-explorer/upload', methods=['POST'])
@login_required
def upload_file():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        current_path = request.form.get('path', '')
        file = request.files.get('file')
        
        if not file:
            return jsonify({'success': False, 'message': 'No file provided'})
        
        # Secure the filename
        filename = secure_filename(file.filename)
        upload_path = os.path.join(COURSE_CONTENT_PATH, current_path, filename)
        
        # Security check to prevent directory traversal
        if not os.path.commonpath([upload_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            return jsonify({'success': False, 'message': 'Invalid path'})
        
        # Check if file already exists
        if os.path.exists(upload_path):
            return jsonify({'success': False, 'message': 'File already exists'})
        
        # Save the file
        file.save(upload_path)
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'file': {
                'name': filename,
                'path': os.path.relpath(upload_path, COURSE_CONTENT_PATH),
                'size': os.path.getsize(upload_path),
                'modified': datetime.fromtimestamp(os.path.getmtime(upload_path)).strftime('%Y-%m-%d %H:%M:%S'),
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error uploading file: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})



@admin_bp.route('/file-explorer/delete', methods=['POST'])
@login_required
def delete_file():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    path = request.json.get('path')
    if not path:
        return jsonify({'success': False, 'message': 'Invalid request'})
    
    file_path = os.path.join(COURSE_CONTENT_PATH, path)
    
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            os.rmdir(file_path)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/file-explorer/content')
@login_required
def get_file_content():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        path = request.args.get('path', '')
        file_path = os.path.join(COURSE_CONTENT_PATH, path)
        
        # Security check
        if not os.path.commonpath([file_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            return 'Invalid path', 400
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return content
        
    except Exception as e:
        current_app.logger.error(f"Error reading file: {str(e)}")
        return str(e), 500

@admin_bp.route('/file-explorer/edit', methods=['POST'])
@login_required
def edit_file():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        data = request.get_json()
        path = data.get('path', '')
        content = data.get('content', '')
        
        if not path:
            return jsonify({'success': False, 'message': 'Invalid request'})
        
        file_path = os.path.join(COURSE_CONTENT_PATH, path)
        
        # Security check
        if not os.path.commonpath([file_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            return jsonify({'success': False, 'message': 'Invalid path'})
            
        # Save the file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({'success': True})
        
    except Exception as e:
        current_app.logger.error(f"Error saving file: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/file-explorer/serve/<path:path>')
@login_required
def serve_file(path):
    if not current_user.is_admin:
        abort(403)
        
    try:
        file_path = os.path.join(COURSE_CONTENT_PATH, path)
        
        # Security check
        if not os.path.commonpath([file_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            abort(404)
            
        return send_file(file_path)
        
    except Exception as e:
        current_app.logger.error(f"Error serving file: {str(e)}")
        abort(500)

@admin_bp.route('/api/get-dynakube-yaml/<int:cluster_id>', methods=['GET'])
def get_dynakube_yaml(cluster_id):
    try:
        yaml_path = os.path.join(current_app.root_path, 'scripts', 'deployment', 'dynakube.yaml')
        
        # Get the specific cluster by ID
        cluster = AKSCluster.query.get_or_404(cluster_id)
        
        if not os.path.exists(yaml_path):
            return jsonify({
                'success': False,
                'message': f'Template file not found at {yaml_path}'
            })
            
        with open(yaml_path, 'r') as file:
            yaml_content = file.read()

        dt_environment = DynatraceEnvironment.query.filter_by(user_id=cluster.user_id).first()
        if not dt_environment:
            return jsonify({
                'success': False,
                'message': 'No Dynatrace environment configured for cluster owner'
            })
        
        base_url = dt_environment.environment_base_url()
        cluster_name = cluster.name.replace('_','-')
        
        template = Template(yaml_content)
        yaml_content = template.render(
            name=cluster_name,
            environment_url=base_url
        )
        
        return jsonify({
            'success': True,
            'content': yaml_content
        })
    except Exception as e:
        current_app.logger.error(f"Error loading dynakube template: {str(e)}")
        return jsonify({
            'success': False,
            'message': str(e)
        }), 400

@admin_bp.route('/file-explorer/create-folder', methods=['POST'])
@login_required
def create_folder():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        path = request.json.get('path', '')
        folder_name = request.json.get('folderName', '').strip()
        
        if not folder_name:
            return jsonify({'success': False, 'message': 'Folder name is required'})
        
        # Create full path
        new_folder_path = os.path.join(COURSE_CONTENT_PATH, path, folder_name)
        
        # Security check to prevent directory traversal
        if not os.path.commonpath([new_folder_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            return jsonify({'success': False, 'message': 'Invalid path'})
        
        # Check if folder already exists
        if os.path.exists(new_folder_path):
            return jsonify({'success': False, 'message': 'Folder already exists'})
        
        # Create the folder
        os.makedirs(new_folder_path)
        
        return jsonify({
            'success': True,
            'message': 'Folder created successfully',
            'folder': {
                'name': folder_name,
                'path': os.path.relpath(new_folder_path, COURSE_CONTENT_PATH)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Error creating folder: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/file-explorer/rename', methods=['POST'])
@login_required
def rename_item():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        old_path = request.json.get('oldPath', '')
        new_name = request.json.get('newName', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'message': 'New name is required'})
        
        # Get full paths
        old_full_path = os.path.join(COURSE_CONTENT_PATH, old_path)
        new_full_path = os.path.join(os.path.dirname(old_full_path), new_name)
        
        # Security checks
        if not os.path.commonpath([old_full_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH or \
           not os.path.commonpath([new_full_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            return jsonify({'success': False, 'message': 'Invalid path'})
        
        # Check if new path already exists
        if os.path.exists(new_full_path):
            return jsonify({'success': False, 'message': 'A file or folder with this name already exists'})
        
        # Rename the item
        os.rename(old_full_path, new_full_path)
        
        return jsonify({
            'success': True,
            'message': 'Item renamed successfully',
            'newPath': os.path.relpath(new_full_path, COURSE_CONTENT_PATH)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error renaming item: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/file-explorer/move', methods=['POST'])
@login_required
def move_item():
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied'})
    
    try:
        source_path = request.json.get('sourcePath', '')
        target_path = request.json.get('targetPath', '')
        
        # Get full paths
        source_full_path = os.path.join(COURSE_CONTENT_PATH, source_path)
        target_full_path = os.path.join(COURSE_CONTENT_PATH, target_path, os.path.basename(source_path))
        
        # Security checks
        if not os.path.commonpath([source_full_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH or \
           not os.path.commonpath([target_full_path, COURSE_CONTENT_PATH]) == COURSE_CONTENT_PATH:
            return jsonify({'success': False, 'message': 'Invalid path'})
        
        # Check if target already exists
        if os.path.exists(target_full_path):
            return jsonify({'success': False, 'message': 'A file or folder with this name already exists in the target directory'})
        
        # Move the item
        os.rename(source_full_path, target_full_path)
        
        return jsonify({
            'success': True,
            'message': 'Item moved successfully',
            'newPath': os.path.relpath(target_full_path, COURSE_CONTENT_PATH)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error moving item: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/admin/file-explorer/read-file')
@login_required
def read_file():
    path = request.args.get('path')
    if not path:
        return jsonify({'success': False, 'message': 'No path provided'})
    
    try:
        with open(path, 'r', encoding='utf-8') as file:
            content = file.read()
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

def code_block_replacer(match):
    language = match.group(1) or 'text'
    code_content = match.group(2).strip()
    line_count = len(code_content.splitlines())
    min_height = 50  # Height for single line
    height_per_line = 20  # Pixels per line
    calculated_height = min(max(min_height, line_count * height_per_line), 400)  # Cap at 400px
    
    return f'''
    <div class="code-editor mb-3" data-language="{language}">
        <div class="code-editor-header d-flex justify-content-between align-items-center p-2">
            <span class="language-label">{language}</span>
            <button class="btn btn-sm btn-outline-light copy-btn">
                <i class="bi bi-clipboard"></i>
            </button>
        </div>
        <div class="code-content" style="height: {calculated_height}px;">{code_content}</div>
    </div>
    '''


