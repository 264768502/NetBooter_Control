#!/usr/bin/env python
import sys,os
import time
import re

import serial

import telnetlib

import httplib
import base64
import string


class NetBooter_Control:
    '''
    Offer NetBooter Control class:
        Support serial/telnet/http control
        Support outlet status checker / power on / power off / reboot
        Power on/off return setting success or fail, but reboot no return

    How to use it:

    From Serial
    NetBooter = NetBooter_Control(mode='serial',serial_port='COM1')
    NetBooter.power_on(1)                              #Return (True,'') for set Outlet 1 ON success
    NetBooter.power_off(5)                             #Return (True,'') for set Outlet 5 OFF success
    NetBooter.reboot(3)                                #No return, use NetBooter internal reboot function, don't suggest to use it
    Outlet3_Status = NetBooter.check_outlet_status(3)  #Return (True,'') for Outlet 3 is ON | (False,'') for OFF

    From HTTP
    NetBooter = NetBooter_Control(mode='http',ip='192.168.1.101')
    NetBooter.power_on(2)                              #Return (True,'') for set Outlet 2 ON success
    NetBooter.power_off(4)                             #Return (True,'') for set Outlet 4 OFF success
    Outlet3_Status = NetBooter.check_outlet_status(3)  #Return (True,'') for Outlet 3 is ON | (False,'') for OFF

    '''
    def __init__(self,mode='serial',serial_port='COM1',id='admin',password='admin',ip='0.0.0.0'):
        '''
        Class init
        Input: mode(serial/telnet/http)
               id/password [for login NetBooter]
               For serial: serial_port([Windows]COM1/COM2/COM3/[Linux]/dev/tty...)
               For telnet/http: ip
        '''
        if not isinstance(mode,str):     raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid mode '+str(mode))
        if not isinstance(id,str):       raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid id '+str(id))
        if not isinstance(password,str): raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid password '+str(password))
        self.mode = mode.lower()
        self.id = id
        self.password = password
        if self.mode == 'serial':
            self.NetBooter_serial = serial.Serial()
            self.NetBooter_serial.port = serial_port
            self.NetBooter_serial.baudrate = 9600
            self.NetBooter_serial.timeout = 3
            self.NetBooter_serial.bytesize = serial.EIGHTBITS
            self.NetBooter_serial.parity = serial.PARITY_NONE
            self.NetBooter_serial.stopbits = serial.STOPBITS_ONE
            self.NetBooter_serial.xonxoff = 0
            try:
                self.NetBooter_serial.open()
            except Exception as e:
                raise Exception(str(e))
            if not self.NetBooter_serial.isOpen():
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Fail to open '+str(serial_port))
            for outlet in xrange(1,6):
                self.power_on(outlet)
        elif self.mode == 'telnet':
            self.ip = ip
            self.NetBooter_telnet = telnetlib.Telnet(self.ip)
        elif self.mode == 'http':
            self.ip = ip
            self.auth = base64.encodestring('%s:%s' % (self.id, self.password)).replace('\n', '')
            self.NetBooter_httpconnection = httplib.HTTPConnection(self.ip,timeout=10)
        self.__check_netbooter__()

    def __check_netbooter__(self):
        if self.mode == 'serial':
            try:
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write('\nsysshow\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                temp1 = self.NetBooter_serial.read(300)
                self.NetBooter_serial.write('\nsysshow\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                temp2 = self.NetBooter_serial.read(300)
                status = temp1+temp2
                self.NetBooter_serial.flushOutput()
            except Exception as e:
                raise Exception(str(e))
            if status.find('System Name') == -1:
                raise Exception('Invalid NetBooter')
        elif self.mode == 'telnet':
            pass
        elif self.mode == 'http':
            NetBooter_Pattern = re.compile(r'Synaccess.*?NetBooter',re.I)
            NetBooter_rly_Pattern = re.compile(r'<a onclick="ajxCmd\(\'(.*?rly.*?)\d\'\);">')
            NetBooter_rb_Pattern  = re.compile(r'<a onclick="ajxCmd\(\'(.*?rb.*?)\d\'\);">')
            try:
                self.NetBooter_httpconnection.putrequest("POST",'')
                self.NetBooter_httpconnection.putheader("Authorization", "Basic %s" % self.auth)
                self.NetBooter_httpconnection.endheaders()
                response = self.NetBooter_httpconnection.getresponse()
                res = response.read()
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Init http connection to NetBooter fail: '+str(e))
            if response.status != 200:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Init http connection to NetBooter fail: '+str(response.status))
            if not NetBooter_Pattern.search(res):
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] http connection is not NetBooter: '+str(res))
            rly_pair = NetBooter_rly_Pattern.search(res)
            if rly_pair:
                self.rly_url = rly_pair.group(1)
            else:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Fail to find NetBooter rly url: '+str(res))
            rb_pair = NetBooter_rb_Pattern.search(res)
            if rb_pair:
                self.rb_url = rb_pair.group(1)
            else:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Fail to find NetBooter rb url: '+str(res))

    def __del__(self):
        if self.mode == 'serial':
            self.NetBooter_serial.close()
        elif self.mode == 'telnet':
            self.NetBooter_telnet.close()
        elif self.mode == 'http':
            self.NetBooter_httpconnection.close()

    def check_outlet_status(self,outlet):
        '''
        Check outlet status
        Input: outlet(1/2/3/4/5)
        Output: True,''(For ON)/False,''(For OFF)/Exception,Exception Reason
        '''
        if outlet not in (1,2,3,4,5,'1','2','3','4','5'):
            raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid NetBooter outlet: '+str(outlet))
        outlet = int(outlet)
        if self.mode == 'serial':
            if not self.NetBooter_serial.readable() or not self.NetBooter_serial.writable():
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] NetBooter Serial not Readable/Writeable')
            try:
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write('\nsysshow\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                temp1 = self.NetBooter_serial.read(300)
                self.NetBooter_serial.write('\nsysshow\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                temp2 = self.NetBooter_serial.read(300)
                status = temp1+temp2
                self.NetBooter_serial.flushOutput()
            except Exception as e:
                raise Exception(str(e))
            try:
                for line in status.split('\n'):
                    if line.find('Outlet Status(1-On, 0-Off. Outlet 1 to 5):') > -1:
                        #Clean Unrecognizable Code
                        line = line[43:].replace('\x00','')
                        #Outlet list should be ['','0/1','0/1','0/1','0/1','0/1','']
                        outlets = line.split(' ')
                        if outlets[outlet] == '0':
                            return False,''
                        elif outlets[outlet] == '1':
                            return True,''
                        else:
                            raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid Status: '+str(outlets))
            except Exception as e:
                return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e)
            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Not find outlet: '+str(status)
        elif self.mode == 'telnet':
            try:
                self.NetBooter_telnet.write('\r\nsysshow\r\n'.encode('ascii'))
                temp = self.NetBooter_telnet.read_until('Note - use WEB access for more settings',2)
            except Exception as e:
                raise Exception(str(e))
            try:
                for line in status.split('\n'):
                    if line.find('Outlet Status(1-On, 0-Off. Outlet 1 to 5):') > -1:
                        #Clean Unrecognizable Code
                        line = line[43:].replace('\x00','')
                        #Outlet list should be ['','0/1','0/1','0/1','0/1','0/1','']
                        outlets = line.split(' ')
                        if outlets[outlet] == '0':
                            return False,''
                        elif outlets[outlet] == '1':
                            return True,''
                        else:
                            raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid Status: '+str(outlets))
            except Exception as e:
                return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e)
            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Not find outlet: '+str(status)
        elif self.mode == 'http':
            res = self.NetBooter_httppost(url="/status.xml")
            if res[0] != True:
                return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] No proper response from NetBooter: '+res[1]
            swoutlet = outlet - 1
            pattern = re.compile(r'<rly%s>(1|0)</rly%s>'%(swoutlet,swoutlet))
            if not pattern.search(res[1]):
                return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Not find proper outlet status: '+res[1]
            status = pattern.search(res[1]).group()[6:7]
            if status == '0':
                return False,''
            elif status == '1':
                return True,''
            else:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid Status: '+str(status))

    def login(self):
        '''
        Login NetBooter for serial/telnet mode
        No output
        '''
        if self.mode == 'serial':
            if not self.NetBooter_serial.writable():
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] NetBooter Serial not Writeable')
            try:
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write('\n!\nlogin\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write(str(self.id)+'\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write(str(self.password)+'\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))
        elif self.mode == 'telnet':
            try:
                self.NetBooter_telnet.write('\r\nlogin\r\n'.encode('ascii'))
                self.NetBooter_telnet.write(str(self.id)+'\r\n'.encode('ascii'))
                self.NetBooter_telnet.write(str(self.password)+'\r\n'.encode('ascii'))
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))

    def power_on(self,outlet):
        '''
        Set specific outlet on
        Input: outlet(1/2/3/4/5)
        Output: True,''[Set success]/False,''[Set fail]/Exception,''
        '''
        if outlet not in (1,2,3,4,5,'1','2','3','4','5'):
            raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid NetBooter outlet: '+str(outlet))
        outlet = int(outlet)

        if self.mode == 'http':
            current_status = self.check_outlet_status(outlet)
            if current_status[0] == True:
                return True,''
            elif current_status[0] == False:
                swoutlet = outlet - 1
                url = "/%s%s"%(self.rly_url,swoutlet)
                res = self.NetBooter_httppost(url)
                if res[0] == True:
                    if res[1] == 'Success! ':
                        new_status = self.check_outlet_status(outlet)
                        if new_status[0] == True:
                            return True,''
                        elif new_status[0] == False:
                            return False,'['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Power on outlet fail2: '+new_status[1]
                        else:
                            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+new_status[1]
                    else:
                        return False,'['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Power on outlet fail1: '+res[1]
                else:
                    return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+res[1]
            else:
                return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+current_status[1]
            time.sleep(2)

        self.login()
        if self.mode == 'serial':
            if not self.NetBooter_serial.writable():
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] NetBooter Serial not Writeable')
            try:
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write('\npset '+str(outlet)+' 1\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                time.sleep(1)
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))

        elif self.mode == 'telnet':
            try:
                self.NetBooter_telnet.write(('\r\npset '+str(outlet)+' 1\r\n').encode('ascii'))
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))

        res_on = self.check_outlet_status(outlet)
        if res_on[0] == True:
            return True,''
        elif res_on[0] == False:
            return False,''
        else:
            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+res_on[1]

    def power_off(self,outlet):
        '''
        Set specific outlet off
        Input: outlet(1/2/3/4/5)
        Output: True,''[Set success]/False,''[Set fail]/Exception,''
        '''
        if outlet not in (1,2,3,4,5,'1','2','3','4','5'):
            raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid NetBooter outlet: '+str(outlet))
        outlet = int(outlet)

        if self.mode == 'http':
            current_status = self.check_outlet_status(outlet)
            if current_status[0] == False:
                return True,''
            elif current_status[0] == True:
                swoutlet = outlet - 1
                url = "/%s%s"%(self.rly_url,swoutlet)
                res = self.NetBooter_httppost(url)
                if res[0] == True:
                    if res[1] == 'Success! ':
                        new_status = self.check_outlet_status(outlet)
                        if new_status[0] == False:
                            return True,''
                        elif new_status[0] == True:
                            return False,'['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Power off outlet fail2: '+new_status[1]
                        else:
                            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+new_status[1]
                    else:
                        return False,'['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Power off outlet fail1: '+res[1]
                else:
                    return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+res[1]
            else:
                return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+current_status[1]
            time.sleep(2)

        self.login()
        if self.mode == 'serial':
            if not self.NetBooter_serial.writable():
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] NetBooter Serial not Writeable')
            try:
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write('\npset '+str(outlet)+' 0\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                time.sleep(1)
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))

        elif self.mode == 'telnet':
            try:
                self.NetBooter_telnet.write(('\r\npset '+str(outlet)+' 0\r\n').encode('ascii'))
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))

        res_off = self.check_outlet_status(outlet)
        if res_off[0] == False:
            return True,''
        elif res_off[0] == True:
            return False,''
        else:
            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+res_off[1]

    def reboot(self,outlet):
        '''
        Set specific outlet reboot by internal reboot function from NetBooter
        Input: outlet(1/2/3/4/5)
        No output
        '''
        if outlet not in (1,2,3,4,5,'1','2','3','4','5'):
            raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Invalid NetBooter outlet: '+str(outlet))
        outlet = int(outlet)

        if self.mode == 'http':
            current_status = self.check_outlet_status(outlet)
            swoutlet = outlet - 1
            url = "/%s%s"%(self.rb_url,swoutlet)
            res = self.NetBooter_httppost(url)
            time.sleep(3)
            if res[0] == True:
                if res[1] == 'Success! ':
                    new_status = self.check_outlet_status(outlet)

        self.login()
        if self.mode == 'serial':
            if not self.NetBooter_serial.writable():
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] NetBooter Serial not Writeable')

            try:
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                self.NetBooter_serial.write('\nrb '+str(outlet)+'\n')
                self.NetBooter_serial.flush()
                self.NetBooter_serial.flushInput()
                self.NetBooter_serial.flushOutput()
                #time.sleep(1)
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))
        elif self.mode == 'telnet':
            try:
                self.NetBooter_telnet.write(('\r\nrb '+str(outlet)+'\r\n').encode('ascii'))
            except Exception as e:
                raise Exception('['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e))

    def NetBooter_httppost(self,url):
        '''
        Common NetBooter http post
        Input: url(/status.xml[for get stauts] or /cmd.cgi?rly=#1[for set power on/off])
        '''
        try:
            self.NetBooter_httpconnection.putrequest("POST", url)
            self.NetBooter_httpconnection.putheader("Authorization", "Basic %s" % self.auth)
            self.NetBooter_httpconnection.endheaders()
            response = self.NetBooter_httpconnection.getresponse()
            res = response.read()
        except Exception as e:
            return 'Exception','['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+']'+str(e)
        if response.status != 200:
            return False,'['+os.path.basename(__file__)+']['+sys._getframe().f_code.co_name+'] Unknown http connection status: '+str(response.status)
        return True,res
