from langchain.embeddings import HuggingFaceEmbeddings
from langchain.docstore.document import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain.vectorstores.faiss import FAISS as Vectorstore

import sentence_transformers
import numpy as np

from plugins.common import settings
from plugins.common import success_print, error_print
from plugins.common import error_helper 
from plugins.common import CounterLock

import re,os,sys,time,chardet
import threading
import pdfplumber
import logging
import argparse

parser = argparse.ArgumentParser(description='知识库配置')
parser.add_argument('-g', type=str, default='group', dest="GroupName",  help="选择知识库目录， 默认Group")
args = parser.parse_args()


sys.path.append(os.getcwd())
#log
logging.basicConfig()
logger = logging.getLogger()
logger.setLevel(logging.ERROR)

group_name = args.GroupName

source_folder = 'zsk/'+group_name
source_folder_path = os.path.join(os.getcwd(), source_folder)

#目标目录不存在就生成一个
if not os.path.exists('memory/'+group_name):
    os.mkdir('memory/'+group_name)

root_path_list = source_folder_path.split(os.sep)
docs = []
vectorstore = None

chunk_size      = int(settings.embedding.size) #分块大小"
chunk_overlap   = int(settings.embedding.overlap) #分块重叠长度
device          = settings.embedding.device #embedding运行设备


try:
    #加载模型库
    from langchain.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(model_name='')
    embeddings.client = sentence_transformers.SentenceTransformer(
        "m3e-base", device=device)
except Exception as e:
    error_helper("embedding加载失败", r"") #https://github.com/l15y/wenda
    raise e

success_print("Embedding 加载完成")

embedding_lock=CounterLock()
vectorstore_lock=threading.Lock()
def clac_embedding(texts, embeddings, metadatas):
    global vectorstore
    with embedding_lock:
        vectorstore_new = Vectorstore.from_texts(texts, embeddings, metadatas=metadatas)
    with vectorstore_lock:
        if vectorstore is None:
            vectorstore = vectorstore_new
        else:
            vectorstore.merge_from(vectorstore_new)

def make_index():
    global docs
    text_splitter = CharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, separator='\n')
    doc_texts = text_splitter.split_documents(docs)
    docs = []
    texts = [d.page_content for d in doc_texts]
    metadatas = [d.metadata for d in doc_texts]
    thread = threading.Thread(target=clac_embedding, args=(texts, embeddings, metadatas))
    thread.start()
    while embedding_lock.get_waiting_threads()>2:
        time.sleep(0.1)

all_files=[]
for root, dirs, files in os.walk(source_folder_path):
    for file in files:
        all_files.append([root, file])
success_print("文件列表生成完成",len(all_files))

#循环文件。开始文本向量
length_of_read=0
for i in range(len(all_files)):
    root, file=all_files[i]
    data = ""
    title = ""
    try:
        file_path = os.path.join(root, file)
        _, ext = os.path.splitext(file_path)
        if ext.lower() == '.pdf':
            #pdf
            with pdfplumber.open(file_path) as pdf:
                data_list = []
                for page in pdf.pages:
                    print(page.extract_text())
                    data_list.append(page.extract_text())
                data = "\n".join(data_list)
        elif ext.lower() == '.txt':
            # txt
            with open(file_path, 'rb') as f:
                b = f.read()
                result = chardet.detect(b)
            with open(file_path, 'r', encoding=result['encoding']) as f:
                data = f.read()
        else:
            print("目前还不支持文件格式：", ext)
    except Exception as e:
        print("文件读取失败，当前文件已被跳过：",file,"。错误信息：",e)
    # data = re.sub(r'！', "！\n", data)
    # data = re.sub(r'：', "：\n", data)
    # data = re.sub(r'。', "。\n", data)
    data = re.sub(r"\n\s*\n", "\n", data)
    data = re.sub(r'\r', "\n", data)
    data = re.sub(r'\n\n', "\n", data)
    length_of_read+=len(data)
    docs.append(Document(page_content=data, metadata={"source": file}))
    if length_of_read > 1e5:
        success_print("处理进度",int(100*i/len(all_files)),f"%\t({i}/{len(all_files)})")
        make_index()
        # print(embedding_lock.get_waiting_threads())
        length_of_read=0

if len(all_files) == 0:
    error_print("目录内没有数据")
    sys.exit(0)
if len(docs) > 0:
    make_index()

while embedding_lock.get_waiting_threads()>0:
    time.sleep(0.1)
success_print("处理进度",100,"%")
with embedding_lock:
    time.sleep(0.1)
    with vectorstore_lock:
        success_print("处理完成")
try:
    vectorstore_old = Vectorstore.load_local(
        'memory/group', embeddings=embeddings)
    success_print("合并至已有索引。如不需合并请删除 memory/"+group_name+" 文件夹")
    vectorstore_old.merge_from(vectorstore)
    vectorstore_old.save_local('memory/'+group_name)
except:
    print("新建索引")
    vectorstore.save_local('memory/'+group_name)
success_print("保存完成")