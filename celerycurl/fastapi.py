import json
import os
from fastapi import FastAPI, Query, HTTPException, Body
from celery.result import AsyncResult
from fastapi.responses import RedirectResponse
from .celerytasks import CeleryTaskManager as celerytasks

fastapp = FastAPI()#root_path="/fastapi")
prefix="/api"

@fastapp.get("/")
async def root():
    return RedirectResponse("/fastapi/docs")

@fastapp.get(prefix+'/status/{task_id}')
def check_status(task_id: str):
    result = AsyncResult(task_id)
    return {'id':task_id, 'status':result.status, 'result':result.result}

@fastapp.get(prefix+'/stop_task_id/{task_id}')
def stop(task_id:str):
    task = celerytasks.revoke.delay(task_id=task_id)
    return {'id':task.id}

@fastapp.get(f"{prefix}/openai_api_key_status/")
def get_api_key_status():
    is_set = "set" if os.getenv('OPENAI_API_KEY') else "not set"
    return {'openai_api_key_status': is_set}

@fastapp.post(f"{prefix}/set_openai_api_key/")
def set_api_key(key: str = Body(..., embed=True)):
    os.environ['OPENAI_API_KEY'] = key
    return {'message': 'API key updated successfully'}

@fastapp.get(f"{prefix}/openai_chat_completions/")
def openai_chat_completions(messages: str = Query(
                                '{"messages":[{"role": "user", "content": "Tell me your name."}]}'),
                            model: str = Query("gpt-3.5-turbo"),
                            stream: bool = Query(True),
                            url: str = Query("https://api.openai.com/v1/chat/completions")):
    try:
        parsed_messages = json.loads(messages)
        if 'messages' not in parsed_messages:
            raise ValueError("Invalid messages format")
                
        task = celerytasks.openai_chat_completions.delay(
            url=url,
            model=model,
            stream=stream,
            messages=parsed_messages['messages'],
            api_key=os.getenv('OPENAI_API_KEY'),
        )
        return {'id': task.id}
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="JSON decoding error in messages")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))