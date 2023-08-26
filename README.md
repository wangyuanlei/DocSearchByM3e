# 基于m3e模型的向量文档搜索

## nvidia信息
nvidia-smi 查看版本

## 安装需要的库
```bash
# 这段一定要先安装
# 需要确认版本， 选择指定的 
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu117
# 安装必要的包
pip3 install -r ./requirements.txt
```
##启动
```bash
启动前需要吧m3e模型 放到m3e-base 目录下
python main.py
```
## 目录说明
```bash
m3e-base 模型
main.py 启动文件
config.yml 配置文件
plugins 插件目录
|_ common.py 基础函数库
requirements.txt 系统安装库文件
memory 训练后的二进制内容存放位置
zsk 知识库源文件
model.py 功能函数库
gen_data.py 本地文本转向量
openapi.json 接口文件
```
##使用说明
### 训练数据
python gen_data.py -g user_11   # -g参数 为执行的库   不填写默认为group

## 接口
http://127.0.0.1:24450/api/v1/redoc