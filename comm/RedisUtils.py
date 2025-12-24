import json
import threading
import time

import redis

## @file
#  
#  @anchor RedisUtils接口库文件


class RedisUtils:
    def __init__(self):
        # 建立连接
        self.host = "localhost"
        self.port=6379
        self.db=0
        self.password=""
        self.rdb = redis.StrictRedis(host = self.host, port=self.port, db=self.db, password=self.password)
        self.pubsub = self.rdb.pubsub()

    def set_data(self,key, data):
        self.rdb.set(key, json.dumps(data))
        return 0

    def set_singledata(self,key, data):
        self.rdb.set(key, data)
        return 0

    # 获得数据
    def get_data(self,key):
        data_str = self.rdb.get(key)
        if data_str is None:
            return False
        data = json.loads(data_str)
        return data
    
    # 获得数据
    def get_singledata(self,key):
        data_str = self.rdb.get(key)
        if data_str is None:
            return False
        return data_str
    
    
    # 获得所有数据
    def get_data_list(self):
        data_list = []
        for key in self.rdb.keys():
            data = self.get_data(key)
            data_list.append(data)
        return data_list

    # 删除数据
    def del_data(self,key):
        self.rdb.rdb.delete(key)
        return 0

    # 获得key的个数
    def key_count(self):
        count = len(self.rdb.rdb.keys())
        return count

    # 清空表
    def clear_db(self):
        self.rdb.rdb.flushdb()

        return 0

    # 插入队列数据,默认插入json字符串格式
    def insert_data(self,db, data):
        self.rdb.lpush(db, json.dumps(data))
        return 0

    # 获得队列一个数据(同时删除)
    def get_one_data(self,db):
        data = self.rdb.rpop(db)
        if data:
            return json.loads(data)
        else:
            return -1

    # 获得队列所有值，不删除
    def get_all_data(self,db):
        return self.rdb.lrange(db, 0, -1)

    # 获得队列长度
    def queue_count(self,db):
        count = self.rdb.llen(db)
        return count

    # 清空队列
    def clear_queue(self,db):
        while True:
            data = self.rdb.rpop(db)
            if data:  # 如果队列不为空
                pass
            else:  # 如果队列为空，sleep
                break

    # 发布消息
    def pub_data(self,key, data):
        self.rdb.publish(key, json.dumps(data))
        return 0

    def pub_singledata(self,key, data):
        self.rdb.publish(key, data)
        return 0

    def sub_data(self,message_type ,channel, callback):
        self.pubsub.subscribe(channel)
        for message in self.pubsub.listen():
            if message['type'] == message_type:
                callback(message['channel'], json.loads(message['data']))
         
    def sub_singledata(self,message_type ,channel, callback):
        self.pubsub.subscribe(channel)
        for message in self.pubsub.listen():
            if message['type'] == message_type:
                callback(message['channel'], message['data'])
                
    def sub_data_multiple_channels(self, message_type, channels, callback):
        for channel in channels:
            self.pubsub.subscribe(channel)
        for message in self.pubsub.listen():
            if message['type'] == message_type:
                callback(message['channel'], json.loads(message['data']))


    def sub_singledata_multiple_channels(self, message_type, channels, callback):
        for channel in channels:
            self.pubsub.subscribe(channel)
        for message in self.pubsub.listen():
            if message['type'] == message_type:
                callback(message['channel'], message['data'])


def sub_callback(channel,data):
        print("channel：" + channel.decode('utf-8'))
        TimeUnix = time.time_ns()/1e9
        print(TimeUnix - data)

if __name__ == "__main__":
    redis_p = RedisUtils()
    message_type = 'message'
    channel_name = "This is a example channel"
    thread = threading.Thread(target=redis_p.sub_data, args=(message_type,channel_name,sub_callback,))
    thread.start()
    
    while True:
        TimeUnix = time.time_ns()/1e9
        temp = TimeUnix
        redis_p.pub_data("This is a example channel",TimeUnix)
        time.sleep(0.0001)
        

