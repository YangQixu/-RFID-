import uos
import time
from machine import UART, Pin

# 创建与MCU的Uart2接口
uart = UART(2, baudrate=115200, tx=17, rx=16)

# 创建GPI和GPO
GPI = Pin(23, Pin.IN)  # 在GPIO2上创建输入引脚
GPO = Pin(22, Pin.OUT, value=1)  # 进入控制模式value=1，没有进入控制模式value=0

# 控制模式
CONTROL_MODE_SINGLE_READ = 0
CONTROL_MODE_CONTINUOUS_READ = 1
CONTROL_MODE_STOP = 2

# 控制模式状态
control_mode = CONTROL_MODE_SINGLE_READ

# 上电初始化命令
initialize_commands = [
    'FF 00 0C 1D 03',  # Refresh
    'FF 01 97 06 4B BB',  # Region
    'FF 02 93 00 05 51 7D',  # Configure_Gen2
    'FF 03 91 02 01 01 42 C5',  # Antenna
    'FF 02 92 04 B0 45 E9'  # Read_Power
]

# 单次读卡命令
single_read_commands = [
    'FF 00 2A 1D 25',  # Clear_Cache
    'FF 05 22 00 00 13 01 F4 2B 19',  # Search
    'FF 03 29 01 FF 00 1B 03'  # Get_data
]

# 连续读卡命令
continuous_read_commands = [
    'FF 03 9A 01 0C 00 A3 5D',  # Turn_off_filter
    'FF 10 2F 00 00 01 22 00 00 05 07 22 10 00 1B 03 E8 01 FF DD 2B'  # Read_Tag
]

# 停止读卡命令
stop_reader_tag_command = 'FF 03 2F 00 00 02 5E 86'

# 发送数据给MCU并处理返回的信息
def send_command(command):
    uart.write(bytes([int(x, 16) for x in command.split()]))  # 发送命令
    print("sending data:", command)
    start_time = time.ticks_ms()  # 记录发送时间

    # 处理返回的数据
    while True:
        if uart.any():
            Received_data = uart.read() #接收返回信息
            Received_hex = ' '.join(['{:02X}'.format(byte) for byte in Received_data])  # 将返回的信息转换为16进制
            print("Received data:", Received_hex)# 打印返回的信息
            break

        # 判断是否超时
        if time.ticks_diff(time.ticks_ms(), start_time) > 2000:
            print("Timeout")
            # TODO: 根据控制模式进行状态判定
            break

# 监测GPI的状态并根据控制模式进行相应的操作
def monitor_gpi():
    global control_mode

    while True:
        if GPI.value() == 1:  # 高电平触发
            start_time = time.ticks_ms()  # 记录触发时间

            while GPI.value() == 1:
                pass

            if time.ticks_diff(time.ticks_ms(), start_time) < 1500:  # 单次读卡
                if control_mode != CONTROL_MODE_SINGLE_READ:
                    control_mode = CONTROL_MODE_SINGLE_READ
                    print("Control mode: Single Read")
                    send_command(initialize_commands[0])  # 上电初始化
                    send_command(single_read_commands[0])  # 清除缓存
            else:  # 连续读卡
                if control_mode != CONTROL_MODE_CONTINUOUS_READ:
                    control_mode = CONTROL_MODE_CONTINUOUS_READ
                    print("Control mode: Continuous Reading")
                    send_command(initialize_commands[0])  # 上电初始化
                    send_command(continuous_read_commands[0])  # 关闭过滤器

        elif GPI.value() == 0:  # 低电平触发
            start_time = time.ticks_ms()  # 记录触发时间

            while GPI.value() == 0:
                pass

            if time.ticks_diff(time.ticks_ms(), start_time) < 1500:  # 强制停止
                if control_mode != CONTROL_MODE_STOP:
                    control_mode = CONTROL_MODE_STOP
                    print("Control mode: Stop")
                    send_command(stop_reader_tag_command)  # 停止读卡

        time.sleep_ms(100)  # 延时一段时间再检测GPI的状态

# 创建GPI和GPO的线程
import _thread

_thread.start_new_thread(monitor_gpi, ())

# 主循环
while True:
    if control_mode == CONTROL_MODE_SINGLE_READ:
        send_command(single_read_commands[1])  # 500ms内检索一次标签
        time.sleep_ms(35)  # 发送指令间隔
        send_command(single_read_commands[2])  # 从模块缓存获取标签数据
        time.sleep_ms(720)  # 发送指令间隔
    elif control_mode == CONTROL_MODE_CONTINUOUS_READ:
        send_command(continuous_read_commands[1])  # 开始读卡
        time.sleep_ms(35)  # 发送指令间隔
    elif control_mode == CONTROL_MODE_STOP:
        send_command(stop_reader_tag_command)  # 停止读卡
        time.sleep_ms(35)  # 发送指令间隔
