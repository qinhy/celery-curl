import os
import sys
import requests
import os
import numpy as np
from celery import Celery
from celery.app import task as Task

IP = 'localhost'
####################################################################################
os.environ.setdefault('FORKED_BY_MULTIPROCESSING', '1')
os.environ.setdefault('CELERY_BROKER_URL', 'redis://'+IP)
os.environ.setdefault('CELERY_RESULT_BACKEND', 'redis://'+IP+'/0')
os.environ.setdefault('CELERY_TASK_SERIALIZER', 'json')
####################################################################################
celery_app = Celery('tasks')

def WrappTask(task:Task):
    def update_progress_state(progress=1.0,msg=''):
        task.update_state(state='PROGRESS',meta={'progress': progress,'msg':msg})
        task.send_event('task-progress', result={'progress': progress})
        
    def update_error_state(error='null'):
        task.update_state(state='FAILURE',meta={'error': error})
    
    task.progress = update_progress_state
    task.error = update_error_state
    return task 

class CeleryTaskManager:    
    @staticmethod
    @celery_app.task(bind=True)
    def revoke(t: Task, task_id: str):
        return celery_app.control.revoke(task_id, terminate=True)
    
    @staticmethod
    @celery_app.task(bind=True)
    def openai_chat_completions(t: Task, messages=[{"role": "user", "content": "Tell me about Server-Sent Events"}],
                            model="gpt-3.5-turbo",
                            stream=True,
                            api_key=os.getenv('OPENAI_API_KEY'),
                            url="https://api.openai.com/v1/chat/completions",):
        t = WrappTask(t)
        t.progress(0.0)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        data = {
            "model": model,
            "stream": stream,
            "messages": messages
        }
        
        if stream:
            result = []
            with requests.post(url, json=data, headers=headers, stream=stream) as response:
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        result.append(decoded_line)
                        t.progress(0.5, decoded_line)
                        
            t.progress(1.0)  
            return result
        else:    
            response = requests.post(url, json=data, headers=headers, stream=False)
            if response.status_code == 200:
                t.progress(1.0)  
                return response.json()
            else:
                response.raise_for_status()

