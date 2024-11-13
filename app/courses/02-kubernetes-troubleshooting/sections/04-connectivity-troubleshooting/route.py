from flask import request, jsonify
from app.courses.utils import section_route, section_init, dt_api_call, execute_command_in_vm, re_deploy_operator

# Each function name must be unique in all the project, so we need to prefix it with the course and section name

@section_init('k8s_test_deployment_section_1_init')
def k8s_test_deployment_section_1_init(**kwargs):
    try:

        return {
            'valid': False,
            'message': 'Section initialization failed'
        }
    except Exception as e:
        return {
            'valid': False,
            'message': f'Section initialization failed: {str(e)}'
        }

@section_route('k8s_test_deployment_section_1_validate')
def k8s_test_deployment_section_1_validate(**kwargs):

    #res = dt_api_call('api/v2/entities', params={'entitySelector': 'type(KUBERNETES_CLUSTER)'})  

    res = execute_command_in_vm('kubectl get pods -n dynatraceew')
    return jsonify({
        'valid': True,
        'message': f'Action completed successfully! {res}'
    })

