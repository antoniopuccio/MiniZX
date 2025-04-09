import network
import urequests as requests
import os
import time
import json
import random
from machine import Pin, I2C, PWM
import ssd1306

# OLED display configuration
i2c = I2C(0, scl=Pin(1), sda=Pin(2))
display = ssd1306.SSD1306_I2C(64, 32, i2c)

# Button configuration
btn_up = Pin(13, Pin.IN, Pin.PULL_UP)
btn_select = Pin(12, Pin.IN, Pin.PULL_UP)
btn_down = Pin(11, Pin.IN, Pin.PULL_UP)
btn_home = Pin(9, Pin.IN, Pin.PULL_UP)

# Buzzer configuration
buzzer = PWM(Pin(10))
buzzer.duty_u16(0)  # Initially off

# Wi-Fi configuration
SSID = "WIFI"
PASSWORD = "password"
SERVER_URL = "http://192.168.1.100:8000"  # Change with your server address

# Folder to save downloaded software
SOFTWARE_DIR = "/software"

# Check if software folder exists, otherwise create it
try:
    os.mkdir(SOFTWARE_DIR)
except OSError:
    pass  # Folder already exists

# Function to play a beep (used for PIN)
def play_pin_beep():
    buzzer.freq(1000)        # 1kHz frequency
    buzzer.duty_u16(32768)   # 50% duty cycle
    time.sleep_ms(100)       # Beep duration
    buzzer.duty_u16(0)       # Turn off buzzer

# Function to play a beep (used for other actions)
def play_beep():
    # You can leave this function empty or remove it if you don't want beeps for other actions
    pass

# BlinkenLights class
class BlinkenLights:
    def __init__(self):
        # Grid dimensions
        self.GRID_WIDTH = 8   # 8 columns of rectangles
        self.GRID_HEIGHT = 4  # 4 rows of rectangles
        
        # Rectangle states (True = visible, False = invisible)
        self.blinkenlights = [[random.randint(0, 1) for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
        
        # Fixed direction for each row
        self.direction = [True, False, True, False]
        
        # Scroll position for each row
        self.scroll_pos = [0] * self.GRID_HEIGHT
        
        # Flag for all dashes on
        self.all_on = False
    
    def update(self):
        # If all_on is True, all dashes are on and we don't update
        if self.all_on:
            return
            
        # Update rectangle states based on fixed direction
        for y in range(self.GRID_HEIGHT):
            # Update scroll position
            if self.direction[y]:
                # Scroll right
                self.scroll_pos[y] += 1
                if self.scroll_pos[y] >= 8:
                    self.scroll_pos[y] = 0
                    # Shift array and add new element
                    self.blinkenlights[y] = [random.randint(0, 1)] + self.blinkenlights[y][:-1]
            else:
                # Scroll left
                self.scroll_pos[y] -= 1
                if self.scroll_pos[y] <= -8:
                    self.scroll_pos[y] = 0
                    # Shift array and add new element
                    self.blinkenlights[y] = self.blinkenlights[y][1:] + [random.randint(0, 1)]
    
    def set_all_on(self):
        # Set all dashes to on
        self.all_on = True
        for y in range(self.GRID_HEIGHT):
            for x in range(self.GRID_WIDTH):
                self.blinkenlights[y][x] = 1
        self.scroll_pos = [0] * self.GRID_HEIGHT
    
    def reset(self):
        # Reset to normal state
        self.all_on = False
        self.blinkenlights = [[random.randint(0, 1) for _ in range(self.GRID_WIDTH)] for _ in range(self.GRID_HEIGHT)]
    
    def draw(self):
        display.fill(0)
        
        # Draw rectangles
        for x in range(self.GRID_WIDTH):
            for y in range(self.GRID_HEIGHT):
                if self.all_on:
                    # When all_on is True, draw all dashes without scrolling
                    screen_x = x * 8 + 1
                    screen_y = y * 8 + 3
                    
                    # Draw always visible rectangle
                    for dx in range(6):
                        display.pixel(screen_x + dx, screen_y, 1)
                        display.pixel(screen_x + dx, screen_y + 1, 1)
                else:
                    # Normal behavior with scrolling
                    screen_x = x * 8 + 1 + self.scroll_pos[y]
                    screen_y = y * 8 + 3
                    
                    # Draw rectangle if visible and within screen
                    if (self.blinkenlights[y][x] and 
                        0 <= screen_x < 64 and 
                        0 <= screen_x + 5 < 64):
                        for dx in range(6):
                            display.pixel(screen_x + dx, screen_y, 1)
                            display.pixel(screen_x + dx, screen_y + 1, 1)
        
        display.show()

# Function to detect button combinations
def check_button_combination():
    # Sequence for Download (btn_down, btn_select, btn_up)
    sequence = []
    start_time = time.time()
    timeout = 5  # 5 seconds to enter PIN
    
    while time.time() - start_time < timeout:
        # Read button states
        down_pressed = not btn_down.value()
        select_pressed = not btn_select.value()
        up_pressed = not btn_up.value()
        
        # Check if any button is pressed
        if down_pressed and not "down" in sequence:
            play_pin_beep()
            sequence.append("down")
            time.sleep_ms(300)  # Debounce
        
        elif select_pressed and not "select" in sequence:
            play_pin_beep()
            sequence.append("select")
            time.sleep_ms(300)  # Debounce
        
        elif up_pressed and not "up" in sequence:
            play_pin_beep()
            sequence.append("up")
            time.sleep_ms(300)  # Debounce
            
        # Check if we have complete sequence
        if len(sequence) == 3:
            if sequence == ["down", "select", "up"]:
                return "download"
            elif sequence == ["up", "select", "down"]:
                return "execute"
            else:
                return None
            
        time.sleep_ms(50)  # Small pause to avoid CPU overload
    
    # Timeout expired
    return None

# Function to connect to Wi-Fi
def connect_wifi():
    display.fill(0)
    display.text("Connecting", 0, 0, 1)
    display.text("to WiFi...", 0, 10, 1)
    display.show()
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if not wlan.isconnected():
        wlan.connect(SSID, PASSWORD)
        
        # Wait for connection with timeout
        max_wait = 20
        while max_wait > 0:
            if wlan.isconnected():
                break
            max_wait -= 1
            time.sleep(1)
        
        if wlan.isconnected():
            display.fill(0)
            display.text("Connected!", 0, 0, 1)
            ip = wlan.ifconfig()[0]
            display.text(ip, 0, 10, 1)
            display.show()
            time.sleep(2)
            return True
        else:
            display.fill(0)
            display.text("Connection", 0, 0, 1)
            display.text("failed!", 0, 10, 1)
            display.show()
            time.sleep(2)
            return False
    else:
        display.fill(0)
        display.text("Already", 0, 0, 1)
        display.text("connected", 0, 10, 1)
        display.show()
        time.sleep(1)
        return True

# Function to get available software list from server
def get_available_software():
    try:
        response = requests.get(f"{SERVER_URL}/list")
        if response.status_code == 200:
            software_list = response.json()
            response.close()
            return software_list
        else:
            display.fill(0)
            display.text("Error:", 0, 0, 1)
            display.text(f"Code {response.status_code}", 0, 10, 1)
            display.show()
            response.close()
            time.sleep(2)
            return []
    except Exception as e:
        display.fill(0)
        display.text("Error:", 0, 0, 1)
        display.text(str(e)[:10], 0, 10, 1)
        display.show()
        time.sleep(2)
        return []

# Function to get local software
def get_local_software():
    try:
        return os.listdir(SOFTWARE_DIR)
    except:
        return []

# Function to download software
def download_software(software_name):
    display.fill(0)
    display.text("Downloading", 0, 0, 1)
    display.text(software_name[:8], 0, 10, 1)
    display.show()
    
    try:
        response = requests.get(f"{SERVER_URL}/download/{software_name}")
        if response.status_code == 200:
            with open(f"{SOFTWARE_DIR}/{software_name}", "w") as f:
                f.write(response.text)
            response.close()
            
            display.fill(0)
            display.text("Download", 0, 0, 1)
            display.text("completed!", 0, 10, 1)
            display.show()
            time.sleep(2)
            return True
        else:
            display.fill(0)
            display.text("Download", 0, 0, 1)
            display.text("failed!", 0, 10, 1)
            display.show()
            response.close()
            time.sleep(2)
            return False
    except Exception as e:
        display.fill(0)
        display.text("Error:", 0, 0, 1)
        display.text(str(e)[:10], 0, 10, 1)
        display.show()
        time.sleep(2)
        return False

# Function to execute software
def execute_software(software_name):
    display.fill(0)
    display.text("Executing", 0, 0, 1)
    display.text(software_name[:8], 0, 10, 1)
    display.show()
    
    try:
        # Save references to important objects
        disp_backup = display
        
        # Software execution
        with open(f"{SOFTWARE_DIR}/{software_name}") as f:
            code = f.read()
        
        # Execute code in separate namespace to avoid conflicts
        namespace = {
            'display': disp_backup,
            'Pin': Pin,
            'I2C': I2C,
            'ssd1306': ssd1306
        }
        exec(code, namespace)
        
        return True
    except Exception as e:
        display.fill(0)
        display.text("Exec Error:", 0, 0, 1)
        display.text(str(e)[:10], 0, 10, 1)
        display.show()
        time.sleep(3)
        return False

# Function to show menu
def show_menu(options, selected=0, title=None):
    display.fill(0)
    
    if title:
        display.text(title, 0, 0, 1)
        y_start = 10
    else:
        y_start = 0
    
    # Show only 2 options at a time due to small display
    visible_options = options[max(0, selected-1):min(len(options), selected+2)]
    offset = max(0, selected-1)
    
    for i, option in enumerate(visible_options):
        # Show indicator for selected option
        prefix = ">" if i + offset == selected else " "
        # Truncate text if too long
        option_text = option[:9]
        display.text(f"{prefix}{option_text}", 0, y_start + i*10, 1)
    
    display.show()

# Download menu
def download_menu():
    # Check WiFi connection
    if not connect_wifi():
        return
    
    display.fill(0)
    display.text("Loading...", 0, 10, 1)
    display.show()
    
    # Get list of available software
    software_list = get_available_software()
    
    if not software_list:
        display.fill(0)
        display.text("No software", 0, 0, 1)
        display.text("available", 0, 10, 1)
        display.show()
        time.sleep(2)
        return
    
    selected = 0
    show_menu(software_list, selected, "Download:")
    
    while True:
        if not btn_up.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            selected = (selected - 1) % len(software_list)
            show_menu(software_list, selected, "Download:")
            time.sleep(0.2)
        
        elif not btn_down.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            selected = (selected + 1) % len(software_list)
            show_menu(software_list, selected, "Download:")
            time.sleep(0.2)
        
        elif not btn_select.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            # Download selected software
            download_software(software_list[selected])
            time.sleep(0.2)
            return
        
        elif not btn_home.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            time.sleep(0.2)
            return
        
        time.sleep(0.1)

# Execution menu
def execute_menu():
    # Get list of local software
    software_list = get_local_software()
    
    if not software_list:
        display.fill(0)
        display.text("No software", 0, 0, 1)
        display.text("installed", 0, 10, 1)
        display.show()
        time.sleep(2)
        return
    
    selected = 0
    show_menu(software_list, selected, "Execute:")
    
    while True:
        if not btn_up.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            selected = (selected - 1) % len(software_list)
            show_menu(software_list, selected, "Execute:")
            time.sleep(0.2)
        
        elif not btn_down.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            selected = (selected + 1) % len(software_list)
            show_menu(software_list, selected, "Execute:")
            time.sleep(0.2)
        
        elif not btn_select.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            # Execute selected software
            execute_software(software_list[selected])
            time.sleep(0.2)
            # Return to main menu after execution
            return
        
        elif not btn_home.value():
            play_pin_beep()  # Use play_pin_beep() instead of play_beep()
            time.sleep(0.2)
            return
        
        time.sleep(0.1)

# Main screen with BlinkenLights
def main_screen():
    blinken = BlinkenLights()
    last_press_time = 0
    press_duration = 0
    pin_mode_active = False
    
    while True:
        # Update and draw BlinkenLights effect
        blinken.update()
        blinken.draw()
        
        # Check if home button is pressed
        if not btn_home.value():
            current_time = time.time()
            
            # If it's the first press, save the time
            if last_press_time == 0:
                last_press_time = current_time
            else:
                # Calculate press duration
                press_duration = current_time - last_press_time
                
                # If pressed for more than 3 seconds, activate PIN mode
                if press_duration >= 3 and not pin_mode_active:
                    play_pin_beep()  # Sound beep when PIN mode activates
                    pin_mode_active = True
                    # Set all dashes to ON
                    blinken.set_all_on()
                    blinken.draw()  # Show all dashes lit up
        else:
            # If button is released
            if pin_mode_active:
                # If we were in PIN mode, now we can check combinations
                action = check_button_combination()
                if action == "download":
                    download_menu()
                    # After using PIN, reset mode and dash states
                    pin_mode_active = False
                    blinken.reset()
                    time.sleep(0.5)  # Prevent multiple presses
                elif action == "execute":
                    execute_menu()
                    # After using PIN, reset mode and dash states
                    pin_mode_active = False
                    blinken.reset()
                    time.sleep(0.5)  # Prevent multiple presses
                else:
                    # Invalid PIN or timeout
                    pin_mode_active = False
                    blinken.reset()
                    time.sleep(0.5)
            
            # Reset timer if button is released
            last_press_time = 0
            press_duration = 0
        
        time.sleep_ms(50)  # Slow down animation for smoothness

# Application startup
def main():
    display.fill(0)
    display.text("Software", 0, 0, 1)
    display.text("Manager", 0, 10, 1)
    display.text("v1.0", 0, 20, 1)
    display.show()
    time.sleep(2)
    
    while True:
        # Show main screen with BlinkenLights
        main_screen()
        
        time.sleep(0.1)  # Prevent excessive CPU usage

# Run application
if __name__ == "__main__":
    main()
