import fastapi, uvicorn
from fastapi import Query
from plugins.common import app
from plugins.common import settings
from pydantic import BaseModel
import model as my_model
#--------------接口定义-------------------
@app.get("/health", summary='健康检查接口',description='返回 is_success:0k 表示服务正常 ',tags=['健康'])
def health():
    return {"is_success": "ok"}
#----------------------------------------
class request_upload_doc(BaseModel):
    title: str = Query(None, description="文档标题")
    memory_name: str = Query(None, description="区块名称")
    content: str = Query(None, description="文档内容")
@app.post("/api/upload_memory", summary='文档上传到缓存',description='返回 is_success:0k 表示提交成功 ',tags=['基础'])
def upload_doc(params_dict: request_upload_doc):
    try:
        params = params_dict.dict()

        title = params.get('title')
        memory_name = params.get('memory_name')
        content = params.get('content')
        print(title,memory_name,content)

        my_model.save_doc_memory(title, memory_name, content)
        return {"is_success": "ok"}
    except Exception as e :
        return str(e)
#----------------------------------------
class request_save_disk(BaseModel):
    memory_name: str = Query(None, description="区块名称")
@app.post("/api/save_disk", summary='缓存保存到硬盘',description='返回 is_success:0k 表示提交成功 no表示失败',tags=['基础'])
def save_disk(params_dict: request_save_disk):
    try:
        params = params_dict.dict()
        memory_name = params.get('memory_name')
        my_model.memory_save_disk(memory_name)
        return {"is_success": "ok"}
    except Exception as e :
        return str(e)
#----------------------------------------
@app.post("/api/delete_menory", summary='删除缓存内区块',description='返回 is_success:0k 表示提交成功 no表示失败',tags=['基础'])
def delete_menory(params_dict: request_save_disk):
    try:
        params = params_dict.dict()
        memory_name = params.get('memory_name')
        my_model.delete_memory(memory_name)
        return {"is_success": "ok"}
    except Exception as e :
        return str(e)
#----------------------------------------
import json
class request_find(BaseModel):
    prompt: str = Query(None, description="查询内容")
    step: str = Query(None, description="读取区块数")
    memory_name: str = Query("group", description="区块名称")
@app.post("/api/find", summary='查询文档',description='返回 is_success:0k 表示提交成功 no表示失败',tags=['基础'])
def find(params_dict: request_find):
    try:
        params = params_dict.dict()
        memory_name = params.get('memory_name')
        step = params.get('step')
        prompt = params.get('prompt')
        if step is None:
            step = int(settings.embedding.count)

        data = my_model.find(prompt,int(step),memory_name)
        req = {"is_success": "ok", "data":data}
        return req
    except Exception as e :
        return str(e)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.http.port,
                log_level='error', loop="asyncio")