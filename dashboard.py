import utime
import sys
import uselect
import machine
import json
from machine import I2C
from lcd_api import LcdApi
from pico_i2c_lcd import I2cLcd

I2C_ADDR     = 0x27
I2C_NUM_COLS = 16
I2C_NUM_ROWS = 2

i2c = I2C(1, sda=machine.Pin(6), scl=machine.Pin(7), freq=400000)     
lcd = I2cLcd(i2c, I2C_ADDR, I2C_NUM_ROWS, I2C_NUM_COLS)

btn1 = machine.Pin(10, machine.Pin.IN)
btn2 = machine.Pin(14, machine.Pin.IN)
        
# Global vars
btn_cd = 0
prev_stream_content = None
prev_line = [None,None]
line_info = [0,2]
Info = [
    'speedMph',
    'speedKph',
    'cruiseSpeedMph',
    'cruiseSpeedKph',
    'cruiseControl',
    'gear',
    'fuelPercentage',
    'engineOn',
    'electricOn',
    'parkingBreakOn'
]

def init_screen_info():
    # Used to double check code version running on Pico
#     lcd.clear()
#     lcd.putstr('Ver. 3')
#     utime.sleep(1)

    lcd.clear()
    lcd.putstr("Initialized")
    lcd.move_to(0,1)
    lcd.putstr("Waiting conn...")

def get_info_labels(info):
    prefix = ''
    suffix = ''
    
    if info[-3:] == 'Mph' or info[-3:] == 'Kph':
        suffix = info[-3:].lower().replace('kp', 'km')
        
    if info[-10:] == 'Percentage':
        suffix = '%'
        
    if info[:5] == 'speed':
        prefix = 'Speed: '            
        
    if info[:11] == 'cruiseSpeed':
        prefix = 'Crus Spd: '
        
    if info == 'cruiseControl':
        prefix = 'Crus Ctrl: '
        
    if info == 'gear':
        prefix = 'Gear: '
        
    if info == 'fuelPercentage':
        prefix = 'Fuel: '
        
    if info == 'engineOn':
        prefix = 'Engine: '
        
    if info == 'electricOn':
        prefix = 'Engine: '
        
    if info == 'parkingBreakOn':
        prefix = 'Park. Break: '
    
    return prefix, suffix

def write_to_clean_screen(line0, line1):
    lcd.clear()
    lcd.move_to(0,0)
    lcd.putstr(f'{line0}')
    lcd.move_to(0,1)
    lcd.putstr(f'{line1}')

def write_to_line(content, line_num, update_from = 0):
    if update_from == -1:
        return
    lcd.move_to(update_from, line_num)
    lcd.putstr(f'{content[update_from:]}')
    
def line_content(line_num, value):
    prefix, suffix = get_info_labels(Info[line_info[line_num]])
    
    if isinstance(value, bool):
        value = 'On' if value else 'Off'
        
    text = f'{prefix}{value}{suffix}'
    return f'{text:16}'

def find_diff_start(prev, current):
    if prev == '' or prev == None:
        return 0;
    end = min(len(prev), len(current))

    for i in range(end):
        if prev[i] != current[i]:
            return i
    return -1
    
def update_values(stream_content = None):
    global prev_stream_content
    if stream_content == None:
        if prev_stream_content == None:
            return
        else:
            stream_content = prev_stream_content
    try:
        json_content = json.loads(stream_content)
        prev_stream_content = stream_content
        print(f'parsed json data: {json_content}')
        
        lines_content = [line_content(0, json_content[Info[line_info[0]]]), line_content(1, json_content[Info[line_info[1]]])]
        if prev_line[0] == None and prev_line[1] == None:
            lcd.clear()
                
        for i in range(2):
            write_to_line(lines_content[i], i, find_diff_start(prev_line[i], lines_content[i]))
            prev_line[i] = lines_content[i]
        
    except ValueError as error:
        print(f'Invalid json format: {error}')
        pass
        
def read_single(spool):
    return(sys.stdin.read(1) if spool.poll(0) else None)

def main_loop():
    try:
        spool=uselect.poll()
        spool.register(sys.stdin,uselect.POLLIN)
                    
        stream_content = ''
        while True:
            listen_to_buttons()
            
            data = read_single(spool)
            if data == '\r' or data == None:
                continue
            elif data == '\n':
                if stream_content == '':
                    continue
                update_values(stream_content)
                stream_content = ''
            else:
                stream_content += data
    except KeyboardInterrupt:
        return
    
def toggle_setting(line):
    line = (line + 1) % len(Info)
    return line
    
def listen_to_buttons():
    global line_info
    global btn_cd
    global prev_stream_content
    
    # Check button cooldown to avoid skipping options
    # for single press (semi-long press)
    # holding button will change options every 250ms
    time_ms = utime.ticks_ms()
    if btn_cd > 0 and time_ms - btn_cd < 250:
        return
    
    try:   
        if btn1.value() == 1:
            btn_cd = utime.ticks_ms()
            line_info[0] = toggle_setting(line_info[0])
            update_values()            
        
        if btn2.value() == 1:
            btn_cd = utime.ticks_ms()
            line_info[1] = toggle_setting(line_info[1])
            update_values()

    except KeyboardInterrupt:
        return
        
init_screen_info()
main_loop()

print('Program exited')


