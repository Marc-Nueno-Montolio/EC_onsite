from flask_socketio import emit
import importlib.util
import os
import time
import threading

class ScriptRunner:
    def __init__(self, socketio):
        self.socketio = socketio
        self.active_scripts = {}
        
    def run_script(self, script_id, script_name):
        if script_id in self.active_scripts:
            return False
            
        script_path = os.path.join('app', 'scripts', f'{script_name}.py')
        
        def wrapper():
            try:
                spec = importlib.util.spec_from_file_location(script_name, script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                while script_id in self.active_scripts:
                    output = module.run()
                    self.socketio.emit('script_output', {
                        'script_id': script_id,
                        'output': output
                    })
                    time.sleep(1)  # Delay between outputs
                    
            except Exception as e:
                self.socketio.emit('script_output', {
                    'script_id': script_id,
                    'output': f'Error: {str(e)}'
                })
                
        thread = threading.Thread(target=wrapper)
        self.active_scripts[script_id] = thread
        thread.start()
        return True
        
    def stop_script(self, script_id):
        if script_id in self.active_scripts:
            del self.active_scripts[script_id]