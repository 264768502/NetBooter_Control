# NetBooter_Control
This a python script which can control NetBooter NP-05B

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
