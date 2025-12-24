import time
import math
import sys
import numpy as np
import PX4MavCtrlV4 as PX4MavCtrl
import socket
import threading
import struct
import math
import copy


from pickle import FALSE
import socket
import threading
import struct
import math
import copy
import time
import math
import sys
import socket
import win_precise_time as acctime
import ctypes
import datetime

## @file
#  
#  @anchor NetUavAPI接口库文件

class CheckInfo:
    def __init__(self):
        ##解包/打包消息格式定义
        #解析格式6i
        self.Header = 123456789  # 校验码
        self.cpID = 0  # 源ID
        self.tgID = -1  # -1表示转发给所有飞机，目标ID
        self.msgID = 30 # 消息的类型，这里是心跳
        self.Resv = 0  # 保留位
        ##消息解包打包
        self.buffformat ='6i'
        self.buffsize = struct.calcsize(self.buffformat)
        
    # def __init__(self,Header,cpID,tgID,msgID,Resv):    
    #     self.Header = Header  # 校验码
    #     self.cpID = cpID  # 源ID
    #     self.tgID = tgID  # -1表示转发给所有飞机，目标ID
    #     self.msgID = msgID # 消息的类型，这里是心跳
    #     self.Resv = Resv  # 保留位
    #     ##消息解包打包
    #     self.buffformat ='6i'
        
class HeartBeartInfo:
    def __init__(self):
        ##心跳信息
        #解析格式3i
        self.CopterID = 1
        self.time_boot =datetime.datetime.now().timestamp()#时间戳  毫秒级
        self.time_lastupdate = datetime.datetime.now().timestamp()#时间戳  毫秒级
        self.vehicleType = 3
        self.FlightMode = 4
        #解析格式2?
        self.hasUpdate = False
        self.system_status = False
        ##消息解包打包
        self.buffformat ='1i2d2i2?'
        self.buffsize = struct.calcsize(self.buffformat)
        
    # def __init__(self,CopterID,time_boot,vehicleType,FlightMode,hasUpdate,system_status):
    #     self.CopterID = CopterID
    #     self.time_boot = time_boot
    #     self.vehicleType = vehicleType
    #     self.FlightMode = FlightMode
    #     #解析格式2?
    #     self.hasUpdate = hasUpdate
    #     self.system_status = system_status



##已经封装好的通用UDP服务，只需要自定义消息体，就能实现多种消息发送
class HeartServer:
    def __init__(self):
        #配置信息
        self.ReceiveIP = '127.0.0.1'
        self.ReceivePort = 39001
        self.SendIP = '127.0.0.1'
        self.SendPort = 39000
        self.RecHeartThreadFlag = True
        self.SendHeartThreadFlag = True
        self.CheckStateThreadFlag = True
        self.DelayTime = 1
        self.BufferSize = 1024
        self.IpAddrMap = {}#通过ip储存地址
        self.IdMap = {}#通过id储存
        self.ConnectIDList = []#通过id储存
        self.ConnectIpAddrList = []#通过ip储存
        self.heartBeartInfo = HeartBeartInfo()
        self.checkInfo = CheckInfo()
        
    def startHeartSer(self):
        self.netSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.netSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.netSender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.netSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.netSock.bind((self.ReceiveIP, self.ReceivePort))
        self.RecHeartThread = threading.Thread(target=self.ReceiveHeartSer, args=())
        self.SendHeartThread = threading.Thread(target=self.SendHeartSer, args=())
               
        self.CheckStateThread = threading.Thread(target=self.CheckConnectState, args=())
        self.RecHeartThread.start()
        self.SendHeartThread.start()
        self.CheckStateThread.start()

    def endHeartSer(self):
        self.RecHeartThreadFlag = False
        self.RecHeartThread.join()
        self.SendHeartThreadFlag = False
        self.SendHeartThread.join()
        self.CheckStateThreadFlag = False
        self.CheckStateThread.join()

    def SendHeartSer(self):
        checkInfo =self.checkInfo
        heartBeartInfo =self.heartBeartInfo
        while self.SendHeartThreadFlag:
            acctime.sleep(self.DelayTime)
            buffsize =checkInfo.buffsize + heartBeartInfo.buffsize 
            heartBeartInfo.time_lastupdate =  datetime.datetime.now().timestamp()
            packet = ctypes.create_string_buffer(buffsize)
            struct.pack_into(checkInfo.buffformat, packet,0,checkInfo.Header,buffsize,checkInfo.cpID,checkInfo.tgID,checkInfo.msgID,checkInfo.Resv)
            struct.pack_into(heartBeartInfo.buffformat, packet, checkInfo.buffsize,heartBeartInfo.CopterID,heartBeartInfo.time_boot,heartBeartInfo.time_lastupdate,heartBeartInfo.vehicleType,heartBeartInfo.FlightMode,heartBeartInfo.hasUpdate,heartBeartInfo.system_status)    
            self.netSender.sendto(packet, (self.SendIP, self.SendPort))

    def CheckConnectState(self):
        while self.CheckStateThreadFlag:
            acctime.sleep(1)
            for id in self.ConnectIDList:

                    refuseTime = int(round((datetime.datetime.now().timestamp() - self.IdMap[id].time_lastupdate)))
                    if refuseTime > 10:         #超过10秒未连接则报警
                        print("{} 号机已失联：{}s".format(id,refuseTime))
                    if refuseTime >= 30:    
                        self.ConnectIDList.remove(id) #超过30秒则移除连接列表       
                   
    def ReceiveHeartSer(self):
        checkInfo = CheckInfo()
        heartBeartInfo = HeartBeartInfo()
        while self.RecHeartThreadFlag:        
            packet, addr = self.netSock.recvfrom(self.BufferSize)
            packetSize = len(packet)
            buffsize = 0
            acctime.sleep(self.DelayTime)
            
            # print(packetSize)
            if  packetSize > 20:
                Header, buffsize,cpID,tgID,msgID,Resv =struct.unpack_from(checkInfo.buffformat, packet, 0)
                if Header == checkInfo.Header and buffsize == packetSize and (checkInfo.cpID == tgID or tgID == -1):
                    if msgID == checkInfo.msgID: 
                        heartBeartInfo.CopterID,heartBeartInfo.time_boot,heartBeartInfo.time_lastupdate, heartBeartInfo.vehicleType, heartBeartInfo.FlightMode,heartBeartInfo.hasUpdate, heartBeartInfo.system_status =struct.unpack_from(heartBeartInfo.buffformat,packet,checkInfo.buffsize)
                        id = heartBeartInfo.CopterID 
                        

                        if self.IdMap.get(id) == None:
                            self.IdMap[id] = copy.deepcopy(heartBeartInfo)#深拷贝  复制值和分配内存  
                            self.IdMap[id].hasUpdate = True
                        else:
                            self.IdMap[id] = copy.copy(heartBeartInfo)#浅拷贝  只复制值
                            self.IdMap[id].hasUpdate = True
                            
                        if  heartBeartInfo.CopterID not in self.ConnectIDList :
                            self.ConnectIDList.append(heartBeartInfo.CopterID)            
                        delayMillis = int(round((datetime.datetime.now().timestamp() - self.IdMap[id].time_lastupdate) * 1000))
                        print("{} 号机延迟为：{}ms".format(id,delayMillis))
                        print("{} 号机已经连接时间为：{}s".format(id, (int)(datetime.datetime.now().timestamp() - self.IdMap[id].time_boot)))
                        

                        #print( heartBeartInfo.CopterID,heartBeartInfo.time_boot, heartBeartInfo.vehicleType, heartBeartInfo.FlightMode ,heartBeartInfo.hasUpdate, heartBeartInfo.system_status) 


# 在这里定义通信结构体
class GlobalPosData:
    def __init__(self):
        self.CopterID=0
        self.hasUpdate=False
        self.time_boot=0
        self.latlonAlt=[0,0,0]
        self.relative_alt=0
        self.vxyz=[0,0,0]
        self.hdg=0
        self.UePosE=[0,0,0]
        
# uavPosGPS = struct.unpack('9d',buf[24:96])
    def __init__(self,cpID,iv):
        self.CopterID=cpID
        self.hasUpdate=True
        self.time_boot=iv[3]
        self.latlonAlt=iv[0:3]
        self.relative_alt=iv[4]
        self.vxyz=iv[5:8]
        self.hdg=iv[8]
        self.UePosE=[0,0,0]
        
# PX4 MAVLink listen and control API and RflySim3D control API
class NetTransNode:
    
    # constructor function
    def __init__(self, mav=PX4MavCtrl.PX4MavCtrler(1)):
        self.mav = mav
        self.CopterID = mav.CopterID
        self.posGPSVect=[]
        
    def startNetServ(self,RecPort=-1,netSimPort=20030,netSimIP='224.0.0.10'):
        """ Program will block until the start signal from sendStartMsg() is received
        """
        # 这里填网络仿真器的接收IP和端口
        self.netSimPort = netSimPort
        self.netSimIP = netSimIP # 使用组播方式
        
        # 默认情况下，使用22000+i的端口作为监听端口，其中i表示飞机ID
        if RecPort<0:
            RecPort = self.CopterID + 22000
        print('port',RecPort)
        
        # 本程序会将数据发送到(netSimPort,netSimIP)，经过网络仿真器中转，再根据目标ID，发往对应飞机的IP和端口
        # 网络仿真器需要从接收到的数据中，读取飞机的IP，同时根据22000+i的端口规则，向对应飞机发送数据
        ANY = '0.0.0.0'
        self.netSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.netSock.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        
        self.netSender= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.netSender.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) 
        
        self.netSock.bind((ANY,RecPort))

        self.RecThread = threading.Thread(target=self.ListenMsgLoop, args=())
        self.RecThreadFlag=True
        self.RecThread.start()
        self.SendThread = threading.Thread(target=self.SendMsgLoop, args=())
        self.SendThreadFlag=True
        self.SendThread.start()
    
    def endNetServ(self):
        self.RecThreadFlag=False
        self.RecThread.join()
        self.SendThreadFlag=False
        self.SendThread.join()        
        
    def ListenMsgLoop(self):
        #print("Waiting for start Msg")
        while True:
            if not self.RecThreadFlag:
                break
            #try:
            buf,addr = self.netSock.recvfrom(65500)
            # print(len(buf))
            # 在这里添加数据处理算法
            if len(buf)>20:
                cksum,dataLen,cpID,tgID,msgID,Resv=struct.unpack('6i',buf[0:24])
                #print(cksum,dataLen,cpID,tgID,msgID,len(buf))
                if cksum==123456789 and dataLen==len(buf) and (self.CopterID == tgID or tgID == -1):
                    # 校验位+长度校验，确保包是正确的
                    #print('Data')
                    if msgID==2: # 如果消息是GLOBAL_POSITION_INT
                        uavPosGPS = struct.unpack('9d',buf[24:96])
                        posGPSStruct = GlobalPosData(cpID,uavPosGPS) # 用构造函数得到结构体
                        # 以设定的地图GPS原点，计算飞机的UE位置
                        posGPSStruct.UePosE = self.mav.geo.lla2ned(posGPSStruct.latlonAlt,self.mav.trueGpsUeCenter)
                        
                        isCopterExist=False
                        for i in range(len(self.posGPSVect)): #遍历数据列表，飞机ID有没有出现过
                            if self.posGPSVect[i].CopterID == cpID: #如果出现过，就直接更新数据
                                isCopterExist=True
                                self.posGPSVect[i] = copy.deepcopy(posGPSStruct)
                                #break
                        if not isCopterExist:#如果没有出现过，就创建一个结构体
                            self.posGPSVect = self.posGPSVect +  [copy.deepcopy(posGPSStruct)] #扩充列表，增加一个元素
                        
            # except:
            #     print("Error to listen to Start Msg!")
            #     sys.exit(0)

    def SendMsgLoop(self):
        self.mav.trigMsgVect =self.mav.trigMsgVect+['GLOBAL_POSITION_INT'] 
        while True:
            self.mav.hasMsgEvent.wait()
            if 'GLOBAL_POSITION_INT' in self.mav.hasMsgDict:
                if self.mav.hasMsgDict['GLOBAL_POSITION_INT']==True:
                    #print(self.mav.uavPosGPS)
                    self.mav.hasMsgDict['GLOBAL_POSITION_INT']=False
                    # Todo: 在这里添加UDP发送代码，将数据发送出去
                    
                    # 多机通信组网协议如下
                    # 校验位，包长度（用于校验），源CopterID，目标TargetID，消息类型，数据包...
                    cksum=123456789 # 校验码
                    dataLen=9*8+6*4 #9维double型数据+校验位 = 总包长度
                    cpID=self.CopterID #源ID
                    tgID=-1  # -1表示转发给所有飞机，目标ID
                    msgID=2 # 消息的类型，这里是GPS坐标
                    Resv=0 # 保留位
                    buf = struct.pack("6i9d",cksum,dataLen,cpID,tgID,msgID,Resv,*self.mav.uavPosGPS)
                    self.netSender.sendto(buf, (self.netSimIP, self.netSimPort))