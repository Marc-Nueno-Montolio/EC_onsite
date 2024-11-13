import random
import time
import json
from datetime import datetime
from app.courses.utils import make_dt_api_call_without_user_env as dt_api_call
from app.models import DynatraceEnvironment

def generate_random_log():
    log_types = [
        # Example 4: JSON parsing examples
        lambda: {
            "intField": random.randint(1, 100),
            "stringField": f"value_{random.randint(1, 1000)}",
            "nested": {
                "nestedStringField1": f"nested1_{random.randint(1, 1000)}",
                "nestedStringField2": f"nested2_{random.randint(1, 1000)}"
            }
        },
        # Example 5: User ID parsing examples
        lambda: f"user ID={random.randint(1000000, 9999999)} Call = {random.randint(100, 999)} Result = {random.randint(0, 5)}",
        lambda: f"UserId = {random.randint(1000000, 9999999)} Call = {random.randint(100, 999)} Result = {random.randint(0, 5)}",
        lambda: f"user id:{random.randint(1000000, 9999999)} Call = {random.randint(100, 999)} Result = {random.randint(0, 5)}",
        # Example 6: Complex message with user and error
        lambda: {
            "intField": random.randint(1, 100),
            "message": f"Error occurred for user {random.randint(10000, 99999)}: {random.choice(['Missing permissions', 'Invalid input', 'Timeout error', 'Connection failed'])}",
            "nested": {
                "nestedStringField1": f"nested1_{random.randint(1, 1000)}",
                "nestedStringField2": f"nested2_{random.randint(1, 1000)}"
            }
        }
    ]
    
    log_content = random.choice(log_types)()
    return {
        'timestamp': datetime.now().isoformat(),
        'content': json.dumps(log_content) if isinstance(log_content, dict) else log_content
    }

def run(stop_event, app, socketio):
    with app.app_context():
        while not stop_event.is_set():
            log_entry = generate_random_log()
            
            envs = DynatraceEnvironment.query.all()
            for env in envs:
                response = dt_api_call(
                    f'{env.environment_api_endpoint()}/api/v2/logs/ingest',
                    env.environment_api_token,
                    method='POST',
                    json=log_entry
                )
            
                #print(f"Sent log_parser example log entry to env {env.environment_id} (Response: {response.status_code})\nContent: {log_entry['content']}")
                socketio.emit('script_output', {
                    'script_id': 'log_gen_parse_examples',
                    'output': f'Sent log entry to env {env.environment_id} (Response: {response.status_code})\nContent: {log_entry["content"]}'
                })
                
            time.sleep(random.uniform(0.5, 2))