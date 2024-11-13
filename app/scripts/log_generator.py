import random
import time
from datetime import datetime
from app.courses.utils import make_dt_api_call_without_user_env as dt_api_call
from app.models import DynatraceEnvironment

def run(stop_event, app, socketio):  # Add app and socketio as parameters
    with app.app_context():
        while not stop_event.is_set():
            # get all dt environments
            log_entry = {
                'timestamp': datetime.now().isoformat(),
                'content': 'This is a test log entry'
            }

            envs = DynatraceEnvironment.query.all()
            for env in envs:
                response = dt_api_call(f'{env.environment_api_endpoint()}/api/v2/logs/ingest', env.environment_api_token, method='POST', json=log_entry)
            
                print(response.status_code)
                socketio.emit('script_output', {
                    'script_id': 'log_gen',
                    'output': f'Sent log entry to env {env.environment_id} (Response: {response.status_code})'
                })
                
            time.sleep(random.uniform(0.5, 2))