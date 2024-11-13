from flask import request, jsonify
from app.courses.utils import section_route

@section_route('test')
def test( **kwargs):
    
    return jsonify({
        'valid': False,
        'message': 'Not here my friend....!'
    })

