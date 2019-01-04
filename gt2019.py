# -*- coding:utf-8 -*-  
import requests
import sys
import json
import time
import re
import os
import io
import base64
from PIL import Image

defaultencoding = 'utf-8'
if sys.getdefaultencoding() != defaultencoding:
    reload(sys)
    sys.setdefaultencoding(defaultencoding)

seatChange = {'O':30, 'M':31, '1':29, '3':28, '4':23}
headers = {
    'Host': 'kyfw.12306.cn',
    'Origin' : 'https://kyfw.12306.cn',
    'X-Requested-With' : 'XMLHttpRequest',
    'Content-Type' : 'application/x-www-form-urlencoded; charset=UTF-8',
    'Referer' : 'https://kyfw.12306.cn/otn/login/init',
    'Accept': '*/*',
    'Accept-Encoding' : 'gzip, deflate, br',
    'Accept-Language' : 'zh-CN,zh;q=0.8',
    'User-Agent' : 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.73 Safari/537.36',
}

def whileTrue(fn):
    def whileTruefun(*args):
        msg = args[1]
        errorTimes = args[2]
        err = 0
        while True:
            if err > errorTimes:
                print('%s' % msg)
                raise Exception,"whileTrue err"
                # sys.exit()
            try:
                fn(*args)
                break
            except Exception as e:
                print('%s, %s'% (msg, e))
                time.sleep(0.1+err/10)
                err += 1
    return whileTruefun

@whileTrue
def downloadStations(*args):
    print('正在下载城市代码...')
    stationUrl = 'https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9035'
    response = requests.get(stationUrl, headers = headers)
    pattern = re.compile('\'(.*?)\'')
    with io.open('stationCode.txt', 'w', encoding="utf-8") as f:
        f.write(pattern.findall(response.text)[0].lstrip('@'))
    print('城市代码下载完毕')

class Train(object):
    def __init__(self, fromStationCode, toStationCode):
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
        self.session = requests.session()
        self.session.headers = headers
        self.session.verify = False
        self.trainDate = ''
        self.fromStationCode = fromStationCode
        self.toStationCode = toStationCode
        self.fromStationTelecode = ''
        self.toStationTelecode = ''
        self.trainSecretStr = ''
        self.trainNo = ''
        self.trainCode = ''
        self.leftTicket = ''
        self.seatType = ''
        self.trainLocation = ''
        self.submitToken = ''
        self.passengerTicketStr = ''
        self.oldPassengerStr = ''
        self.orderId = ''
        self.getjsonback = ''
        self.postdata = ''
        self.uuid = ''


    @whileTrue
    def login_qr64(self, *args):#扫二维码登录
        qrUrl = "https://kyfw.12306.cn/passport/web/create-qr64"
        data = {
            'appid': 'otn'
        }
        self.postjson('获取二维码出现错误，退出程序', 10, qrUrl, data)
        with open('qr64.jpg', 'wb') as f:
            f.write(base64.b64decode(self.getjsonback['image']))
        self.uuid = self.getjsonback['uuid']
        img=Image.open('qr64.jpg')
        img.show()
        
        print('等待扫码')
        checkUrl = "https://kyfw.12306.cn/passport/web/checkqr"
        data = {
            'appid': 'otn',
            'uuid': self.uuid
        }
        while True:
            response = self.session.post(checkUrl, data = data)
            try:
                if response.json()['result_code'] == '2':
                    self.session.cookies['uamtk'] = response.json()['uamtk']
                    print "扫码成功"
                    break
                else:
                    time.sleep(1)
            except Exception as e:
                time.sleep(1)
                pass

        print('第一次验证')
        url = 'https://kyfw.12306.cn/passport/web/auth/uamtk'
        data = {
            'appid': 'otn'
        }

        self.postjson('第一次验证出现错误，退出程序', 10, url, data)
        userVerify = self.getjsonback
        if userVerify['result_code'] != 0:
            print('验证失败(uamtk) code:{}'.format(userVerify['result_code']))
        
        print('第二次验证')
        url = 'https://kyfw.12306.cn/otn/uamauthclient'
        newapptk = userVerify['newapptk']
        data = {
            'tk': newapptk
        }
        self.postjson('第二次验证出现错误，退出程序', 10, url, data)
        userVerify2 = self.getjsonback
        print('验证通过 用户为:%s'% userVerify2['username'].encode('utf-8')) 

    @whileTrue
    def postjson(self, *args):
        url = args[2]
        data = args[3]
        response = self.session.post(url, data = data)
        self.getjsonback = response.json()         

    @whileTrue
    def getjson(self, *args):
        url = args[2]
        response = self.session.get(url)
        self.getjsonback = response.json()

    @whileTrue
    def findTicket(self, *args):
        retimes = -1
        while True:
            dataLen = len(trainDateList)
            trainDate = trainDateList[(retimes+1)%dataLen]
            queryUrl = 'https://kyfw.12306.cn/otn/leftTicket/queryZ?leftTicketDTO.train_date={}&leftTicketDTO.from_station={}&leftTicketDTO.to_station={}&purpose_codes=ADULT'.format(
            trainDate, self.fromStationCode, self.toStationCode)
            self.trainDate = trainDate
            self.getjson('查询出现错误，退出程序', 20, queryUrl)
            trainList1 = self.getjsonback['data']['result']
            
            trainDict = {}
            for temp in trainList1:
                sp = temp.split('|')
                if sp[3] in trainName:
                    trainDict[sp[3]] = sp
            trainDetailSplit = []
            self.seatType = ''
            for trainTemp in trainName:
                if trainTemp in trainDict:
                    trainDetailSplit = trainDict[trainTemp]
                    for seat in chooseSeat:
                        if trainDetailSplit[seatChange[seat]] != '' and trainDetailSplit[seatChange[seat]] != u'无' and trainDetailSplit[seatChange[seat]] != u'*':
                            self.seatType = seat
                            break 
                    if self.seatType != '':
                        break
                    else:
                        trainDetailSplit = []
            
            if trainDetailSplit != []:
                self.trainSecretStr = trainDetailSplit[0]
                self.trainNo = trainDetailSplit[2]
                self.trainCode = trainDetailSplit[3]
                self.leftTicket = trainDetailSplit[12]
                self.fromStationTelecode = trainDetailSplit[6]
                self.toStationTelecode = trainDetailSplit[7]
                self.trainLocation = trainDetailSplit[15]
                print('查询次数:%s,车次:%s,选座:%s,二等:%s,一等:%s' % (retimes,trainDetailSplit[3],self.seatType,trainDetailSplit[30],trainDetailSplit[31]))
                return
            else:
                retimes += 1
                #每120次,打印查询次数 并检验登录状态
                if retimes%120 == 0:
                    userCheckError = 0
                    while retimes > 1:
                        if userCheckError > 10:
                            print('查票阶段 用户登录检测失败，退出程序')
                            sys.exit()
                        url = 'https://kyfw.12306.cn/otn/login/checkUser'
                        try:
                            self.postjson('检测登录状态1', 10, url, {})
                            result = self.getjsonback
                            if not result['data']['flag']:
                                print('用户未登录checkUser')
                                userCheckError += 1
                                self.login_qr64('登录出错', 10)
                                continue
                            break
                        except:
                            time.sleep(1)
                            userCheckError += 1
                sys.stdout.write("\r当前刷新次数:{0}".format(retimes))
                sys.stdout.flush()         
                time.sleep(1)


    def choosePassenger(self,message):
        passengerList = message['data']['normal_passengers']
        pessengerName = player
        pessengerDetail = dict()
        for p in passengerList:
            if pessengerName == p['passenger_name']:
                pessengerDetail = {
                    'passenger_flag' : p['passenger_flag'],
                    'passenger_type' : p['passenger_type'],
                    'passenger_name' : p['passenger_name'],
                    'passenger_id_type_code' : p['passenger_id_type_code'],
                    'passenger_id_no' : p['passenger_id_no'],
                    'mobile_no' : p['mobile_no']
                }
                return pessengerDetail

    @whileTrue
    def bookingTicket(self, *args):
        self.findTicket('查询出错', 30)

        # 1 checkUser +++++++++++++++++++++++++++++++++++++++++++++
        self.session.headers['Referer'] = 'https://kyfw.12306.cn/otn/leftTicket/init'
        url = 'https://kyfw.12306.cn/otn/login/checkUser'
        self.postjson('检测登录状态2', 10, url, {})
        result = self.getjsonback
        print('验证登录状态checkUser')
        if not result['data']['flag']:
            print('用户未登录checkUser')
            self.login_qr64('登录出错', 10)
        print('验证登录状态成功checkUser')

        # 2 submitOrderRequest+++++++++++++++++++++++++++++++++++++
        print('正在提交订单...')
        url = 'https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest'
        data = 'secretStr={}&train_date={}&back_train_date={}&tour_flag=dc&purpose_codes=ADULT&query_from_station_name={}&query_to_station_name={}&undefined'.format(
        self.trainSecretStr, self.trainDate, time.strftime("%Y-%m-%d", time.localtime(time.time())), fromStationName, toStationName)
        errtimes = 0
        while True:
            self.postjson('提交订单出现错误，退出程序', 5, url, data)
            result = self.getjsonback
            
            if result['status']:
                print('提交订单成功')
                break
            elif errtimes == 10:
                a = 1/0
            else:
                print('提交订单失败')
                print result
                errtimes += 1
                time.sleep(findtime)
            

        # 3 initDC+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
        data = '_json_att='
        pattern = re.compile('globalRepeatSubmitToken = \'(.*?)\'')
        pattern2 = re.compile("key_check_isChange':'(.*?)'")
        response = self.session.post(url, data = data)
        self.submitToken = pattern.findall(response.text)[0]
        self.keyCheckIsChange = pattern2.findall(response.text)[0]

        # 4 getPassengerDTOs++++++++++++++++++++++++++++++++++++++++++++++++++++++
        print('正在获取乘客信息')
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs'
        data = {
            '_json_att' : '',
            'REPEAT_SUBMIT_TOKEN' : self.submitToken
        }

        self.postjson('正在获取乘客信息出现错误，退出程序', 15, url, data)
        result = self.getjsonback
        pd = self.choosePassenger(result)
        print('获取信息成功')
        #self.chooseSeat()

        # 5 checkOrderInfo++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        print('正在验证订单...')
        self.passengerTicketStr = self.seatType + ',' + pd['passenger_flag'] + ',' + pd['passenger_type'] + ',' + pd['passenger_name'] + ',' + pd['passenger_id_type_code'] + ',' + pd['passenger_id_no'] + ',' + pd['mobile_no'] + ',N'
        self.oldPassengerStr =  pd['passenger_name'] + ',' + pd['passenger_id_type_code'] + ',' + pd['passenger_id_no'] + ',' + pd['passenger_type'] + '_'
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo'
        data = {
            'cancel_flag':'2',
            'bed_level_order_num':'000000000000000000000000000000',
            'passengerTicketStr':self.passengerTicketStr,
            'oldPassengerStr':self.oldPassengerStr,  # dc 单程
            'tour_flag':'dc',  # adult 成人票
            'randCode':'',
            'whatsSelect':'1',
            '_json_att':'',
            'REPEAT_SUBMIT_TOKEN':self.submitToken
        }
        self.postjson('验证订单失败，退出程序', 15, url, data)
        result = self.getjsonback


        # 6 getQueueCount+++++++++++++++++++++++++++++++++++++++++++++++++++++++++ 跳过此步骤不影响抢票流程
        # url = 'https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount'
        # dateGMT = time.strftime('%a %b %d %Y %H:%M:%S  GMT+0800', time.strptime(self.trainDate, '%Y-%m-%d'))
        # data = {
        #     'train_date' : dateGMT,
        #     'train_no' : self.trainNo,
        #     'stationTrainCode' : self.trainCode,
        #     'seatType' : self.seatType,
        #     'fromStationTelecode' : self.fromStationTelecode,
        #     'toStationTelecode' : self.toStationTelecode,
        #     'leftTicket' : self.leftTicket,
        #     'purpose_codes' : '00',
        #     'train_location' : self.trainLocation,
        #     '_json_att' : '',
        #     'REPEAT_SUBMIT_TOKEN' : self.submitToken
        # }
        # self.postjson('getQueueCount有误，退出程序', 15, url, data)
        # result = self.getjsonback

        # 7 confirmSingleForQueue++++++++++++++++++++++++++++++++++++++++++++++++++
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue'
        data = {
            'passengerTicketStr' : self.passengerTicketStr,
            'oldPassengerStr' : self.oldPassengerStr,
            'randCode' : '',
            'purpose_codes' : '00',
            'key_check_isChange' : self.keyCheckIsChange,
            'leftTicketStr' : self.leftTicket,
            'train_location' : self.trainLocation,
            'choose_seats' : '1F', #优先f
            'seatDetailType' : '000',
            'whatsSelect' : '1',
            'roomType' : '00',
            'dwAll' : 'N',
            '_json_att' : '',
            'REPEAT_SUBMIT_TOKEN' : self.submitToken
        }

        self.postjson('订票有误，退出程序', 10, url, data)
        result = self.getjsonback
        if not result['data']['submitStatus']:
            print('订票失败，退出程序:%s, %s' % (result, result['data']['errMsg']))
            a = 1/0
        print('nima:%s' % result)

        # 8 queryOrderWaitTime+++++++++++++++++++++++++++++++++++++++++
        url = 'https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random={}&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN={}'.format(
            str(round(time.time() * 1000)),self.submitToken)


        self.getjson('queryOrderWaitTime错误，退出程序', 10, url)
        result = self.getjsonback  
        if "queryOrderWaitTimeStatus" in result["data"] and result["data"]["queryOrderWaitTimeStatus"]:
            if result['data']['waitCount'] == 0:  
                print('订单提交成功：%s' % result)
            else:
                print('订单排队个数：%s, 时间：%s' % (result['data']['waitCount'], result['data']['waitTime']))
        else:
            print('订单提交结果：%s' % result)
        self.orderId = result['data']['orderId']


        url = 'https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue'
        data = 'orderSequence_no={}&_json_att=&REPEAT_SUBMIT_TOKEN={}'.format(self.orderId,self.submitToken)
        
        self.postjson('8订票有误，退出程序', 10, url, data)
        result = self.getjsonback
        if result['data']['submitStatus']:
            print('订票成功，请登录12306查看')
        else:
            print('查询订单有误,请登录12306查看具体订单情况 %s,%s' % (result, result['data']['errMsg']))
            a = 1/0


if __name__ == "__main__":
    # 读取配置 获取购票人等信息
    jsonname = sys.argv[1]
    findtime = sys.argv[2]
    f = io.open("%s.json"%jsonname, encoding='utf-8')  
    setting = json.load(f)
    trainName = setting["trainName"]
    player = setting["player"]
    trainDateList = setting["trainDateList"]
    fromStationName = setting["fromStationName"]
    toStationName = setting["toStationName"]
    #硬座 : '1', 一等 : 'M', 二等 : 'O',  硬卧 : '3', 软卧 : '4'         
    chooseSeat = setting["chooseSeat"]

    ## 获取配置的地点代码
    if os.path.exists('./stationCode.txt'):
        pass
    else:
        downloadStations('', '下载城市数据出错', 10)

    with io.open('stationCode.txt', 'r', encoding='utf-8') as f:
        stationsStr = f.read()
    stations = stationsStr.split('@')
    for s in stations:
        tempStationSplit = s.split('|')
        if tempStationSplit[1] == fromStationName:
            fromStationCode = tempStationSplit[2]
        elif tempStationSplit[1] == toStationName:
            toStationCode = tempStationSplit[2]
        else:
            pass  
    
    ## 抢票逻辑
    t = Train(fromStationCode, toStationCode)
    t.login_qr64('登录出错', 15)
    t.bookingTicket('订票出错', 20)
