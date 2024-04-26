import json
import os
from fastapi import FastAPI, Query, HTTPException, Body
from celery.result import AsyncResult
from fastapi.responses import RedirectResponse
from .celerytasks import CeleryTaskManager as celerytasks
from .celerytasks import celery_app

fastapp = FastAPI()#root_path="/fastapi")
prefix="/api"

@fastapp.get("/")
async def root():
    return RedirectResponse("/fastapi/docs")

@fastapp.get(prefix+'/status/{task_id}')
def check_status(task_id: str):
    result = AsyncResult(task_id)
    return {'id':task_id, 'status':result.status, 'result':result.result}

@fastapp.get(prefix+'/stop/{task_id}')
def stop(task_id:str):
    task = celerytasks.revoke.delay(task_id=task_id)
    return {'id':task.id}

def get_task_result(task_id: str):
    task = celery_app.AsyncResult(task_id)
    if not task.ready():
        return {"status": "pending"}
    if task.state == 'FAILURE':
        return {"status": "failed", "error": str(task.result)}
    return {"result": task.result}

@fastapp.get(prefix+"/task_result/{task_id}")
def task_result(task_id: str):
    try:
        return get_task_result(task_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@fastapp.get(f"{prefix}/openai_api_key_status/")
def get_api_key_status():
    is_set = "set" if os.getenv('OPENAI_API_KEY') else "not set"
    return {'openai_api_key_status': is_set}

@fastapp.post(f"{prefix}/set_openai_api_key/")
def set_api_key(key: str = Body(..., embed=True)):
    os.environ['OPENAI_API_KEY'] = key
    return {'message': 'API key updated successfully'}

@fastapp.get(f"{prefix}/openai/chat/completions/")
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

@fastapp.get(f"{prefix}/openai/embeddings/")
def openai_embeddings(input_text: str = Query("Your text string goes here", alias="input"),
                        model: str = Query("text-embedding-3-small"),
                        url: str = Query("https://api.openai.com/v1/embeddings")):
    try:
        task = celerytasks.openai_embeddings.delay(
            url=url,
            input_text=input_text,
            model=model,
            api_key=os.getenv('OPENAI_API_KEY'),
        )
        return {'id': task.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
@fastapp.get(f"{prefix}/openai/audio/speech/")
def openai_audio_speech(input: str = Query("Today is a wonderful day to build something people love!"),
                        model: str = Query("tts-1"), 
                        voice: str = Query("alloy"),
                        url: str = Query("https://api.openai.com/v1/audio/speech"),
                        output_file: str = Query("speech.mp3")):
    try:
        task = celerytasks.openai_audio_speech.delay(
            input=input,
            model=model,
            voice=voice,
            url=url,
            output_file=output_file,
            api_key=os.getenv('OPENAI_API_KEY'),
        )
        return {'id': task.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))