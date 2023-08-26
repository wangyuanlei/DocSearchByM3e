from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores.faiss import FAISS as Vectorstore
from langchain.text_splitter import CharacterTextSplitter
from langchain.docstore.document import Document
import re
import numpy as np
import sentence_transformers
from plugins.common import settings
from plugins.common import error_helper 
from plugins.common import success_print 

try:
    device     = settings.embedding.device #embedding运行设备
    embeddings = HuggingFaceEmbeddings(model_name='')
    embeddings.client = sentence_transformers.SentenceTransformer(
        "m3e-base", device=device)
except Exception as e:
    error_helper("embedding加载失败", r"README.MD") 
    raise e

vectorstores={}
divider='\n'
#保存文档内容到内存
def save_doc_memory(title, memory_name, content):
    #替换多余空行
    content = re.sub(r"\n\s*\n", "\n", content)
    content = re.sub(r'\r', "\n", content)
    content = re.sub(r'\n\n', "\n", content)
    docs=[Document(page_content=content, metadata={"source":title })]
    text_splitter = CharacterTextSplitter(
                chunk_size=20, chunk_overlap=0, separator='\n')
    doc_texts = text_splitter.split_documents(docs)
    texts = [d.page_content for d in doc_texts]
    metadatas = [d.metadata for d in doc_texts]

    vectorstore_new = Vectorstore.from_texts(texts, embeddings, metadatas=metadatas)
    vectorstore=get_vectorstore(memory_name)

    if vectorstore is None:
        vectorstores[memory_name]=vectorstore_new
    else:
        vectorstores[memory_name].merge_from(vectorstore_new)
    return True

#文档内容获得指定索引内容
def get_doc_by_id(id,memory_name):
    return vectorstores[memory_name].docstore.search(vectorstores[memory_name].index_to_docstore_id[id])

#加载模块
def get_vectorstore(memory_name):
    try:
        return vectorstores[memory_name]
    except Exception  as e:
        try:
            vectorstores[memory_name] = Vectorstore.load_local(
                'memory/'+memory_name, embeddings=embeddings)
            return vectorstores[memory_name]
        except Exception  as e:
            success_print("没有读取到RTST记忆区%s，将新建。"%memory_name)
    return None


#2段字符串相识拼接
def process_strings(A, C, B):
    common = ""
    for i in range(1, min(len(A), len(B)) + 1):
        if A[-i:] == B[:i]:
            common = A[-i:]
    if common:
        return A[:-len(common)] + C + B
    else:
        return A + B
#获得文档标题
def get_title_by_doc(doc):
    return re.sub('【.+】', '', doc.metadata['source'])

#获得文档内容
def get_doc(id,score,step,memory_name):
    doc = get_doc_by_id(id,memory_name)
    final_content=doc.page_content
    if step > 0:
        for i in range(1, step+1):
            try:
                doc_before=get_doc_by_id(id-i,memory_name)
                if get_title_by_doc(doc_before)==get_title_by_doc(doc):
                    final_content=process_strings(doc_before.page_content,divider,final_content)
            except:
                pass
            try:
                doc_after=get_doc_by_id(id+i,memory_name)
                if get_title_by_doc(doc_after)==get_title_by_doc(doc):
                    final_content=process_strings(final_content,divider,doc_after.page_content)
            except:
                pass
    if doc.metadata['source'].endswith(".pdf") or doc.metadata['source'].endswith(".txt"):
        title=f"[{doc.metadata['source']}](/txt/{doc.metadata['source']})"
    else:
        title=doc.metadata['source']
    return {'title': title,'content':re.sub(r'\n+', "\n", final_content),"score":int(score)}

#搜索
def find(s,step = 0,memory_name="group"):
    try:
        embedding = get_vectorstore(memory_name).embedding_function(s)
        scores, indices = vectorstores[memory_name].index.search(np.array([embedding], dtype=np.float32), int(settings.embedding.count))
        docs = []
        for j, i in enumerate(indices[0]):
            if i == -1:
                continue
            if scores[0][j]>260:continue
            docs.append(get_doc(i,scores[0][j],step,memory_name))

        return docs
    except Exception as e:
        print(e)
        return []

#缓存保存到硬盘
def memory_save_disk(memory_name):
    vectorstores[memory_name].save_local('memory/'+memory_name)

#删除缓存
def delete_memory(memory_name):
    del vectorstores[memory_name]