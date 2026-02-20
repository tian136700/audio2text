import requests
import json
import time
from requests_toolbelt.multipart.encoder import MultipartEncoder
#  以通过文件方式提交批量任务，任务将异步执行，在24小时内返回结果，费用仅为实时调用的30%。
#
# 文件保存时间： 上传的文件和接口返回的文件均按照文件生成的时间开始计时，保存 48h。


class BatchTask:
    def __init__(self,path,passward):
        # self.path = path
        self.password = passward
        self.header = {
            "Authorization": f'Bearer {passward}',
            "Content-Type": "application/json"
        }
        self.file = self.getFileUrl(path)

    # 上传文件获取链接
    def getFileUrl(self,path):
        url = 'https://spark-api-open.xf-yun.com/v1/files'

        formData = MultipartEncoder(
            fields={
                "purpose": "batch",
                "file":(path, open(path, 'rb'), 'text/plain')
            }
        )
        headers= {
            "Authorization": f'Bearer {self.password}',
            "Content-Type": formData.content_type
        }

        response = requests.post(url= url,data= formData, headers= headers).text
        #打印返回内容
        print("上传文件结果：",response)

        resp = json.loads(response)
        # print(resp)

        return resp['id']

    #创建任务并返回taskid
    def createTask(self):
        url = 'https://spark-api-open.xf-yun.com/v1/batches' #创建任务接口地址

        # data = MultipartEncoder()
        body ={
            "input_file_id":self.file,
            "endpoint":"/v1/chat/completions",
            "completion_window":"24h"
        }
        print(body)
        response = requests.post(url=url,json= body,headers= self.header).text
        print("创建batch 任务结果：",response)
        resp = json.loads(response)
        batch_id = resp['id']

        return batch_id

    def getfile(self,fileid):
        url = f'https://spark-api-open.xf-yun.com/v1/files/{fileid}/content'
        reponse = requests.get(url= url,headers= self.header).text
        return reponse

    #查询结果
    def getResult(self,batch_id):

        url = f'https://spark-api-open.xf-yun.com/v1/batches/{batch_id}'


        while (True):
            response = requests.get(url=url, headers=self.header).text

            resp = json.loads(response)
            if('completed' == resp['status']):
                output_file_id = resp['output_file_id']
                result = self.getfile(output_file_id)
                print("获得结果：",result)
                return result

            time.sleep(3)


if __name__ =='__main__':

    #创建任务对象
    batch = BatchTask("data/batch.jsonl","ijbKTVqdTNCvANfEAooU:LaWCiRSAkQZUVMRDtUnY")  # 文档路径 ，http协议 的passward

    #创建batch任务
    batch_id = batch.createTask()

    #轮询获取batch任务结果
    result= batch.getResult(batch_id)

    print(result)


