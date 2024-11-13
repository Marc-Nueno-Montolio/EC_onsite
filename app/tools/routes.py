from flask import render_template, jsonify, current_app
from app.tools import tools_bp as bp
from flask_login import login_required, current_user
import os
from app.models import *


@bp.route('/')
@login_required
def list():
    # Get user's Dynatrace environment
    dt_environment = DynatraceEnvironment.query.filter_by(user_id=current_user.id).first()
    
    
    # Get user's AKS clusters
    aks_clusters = AKSCluster.query.filter_by(user_id=current_user.id).all()
    
    # Get cluster's deployments
    deployments = []
    for cluster in aks_clusters:
        cluster_deployments = Deployment.query.filter_by(cluster_id=cluster.id).all()
        deployments.extend(cluster_deployments)
    
    # Get VMs linked to user's clusters
    cluster_vms = []
    for cluster in aks_clusters:
        if cluster.vm:
            cluster_vms.append({
                'cluster_name': cluster.name,
                'vm': cluster.vm
            })
    
    return render_template('tools/list.html',
                         dt_environment=dt_environment,
                         deployments=deployments,
                         aks_clusters=aks_clusters,
                         cluster_vms=cluster_vms)