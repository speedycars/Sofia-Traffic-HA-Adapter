from bs4 import BeautifulSoup
import datetime
import time
import configparser
import ast
import pathlib
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from paho.mqtt import client as mqtt_client


config_path = pathlib.Path(__file__).parent.absolute() / "config" / "config.cfg"
config = configparser.ConfigParser()
config.read(config_path, encoding='utf-8')

broker = str(config.get('CONFIG', 'broker'))
port = int(config.get('CONFIG', 'port'))
username = str(config.get('CONFIG', 'username'))
password = str(config.get('CONFIG', 'password'))
stops = ast.literal_eval(config.get('CONFIG', 'stops'))
freq = int(config.get('CONFIG', 'freq'))

service = Service()
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-search-engine-choice-screen')
options.add_argument('--disable-gpu')
options.add_argument("--disable-cache")
options.add_argument("--disable-crash-reporter");
options.add_argument("--disable-crashpad-for-testing");
options.add_argument("--disable-oopr-debug-crash-dump");
options.add_argument("--no-crash-upload");
options.add_argument('--no-sandbox')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--incognito')
options.add_argument('--disable-dev-shm-usage')

url = "https://www.sofiatraffic.bg/bg/public-transport"
client_id = f'mqttsofiatraffic'
total_i = 0
dictt = {'А':'a', 'Б':'b', 'В':'v', 'Г':'g', 'Д':'d', 'Е':'e', 'Ж':'zh', 'З':'z', 'И':'i', 'Й':'y', 'К':'k', 'Л':'l', 'М':'m', 'Н':'n', 'О':'o', 'П':'p', 'Р':'r', 'С':'s', 'Т':'t', 'У':'u', 'Ф':'f', 'Х':'h', 'Ц':'ts', 'Ч':'ch', 'Ш':'sh', 'Щ':'sht', 'Ъ':'a', 'Ь':'y', 'Ю':'yu', 'Я':'ya'}
table  = str.maketrans(dictt)

while True:
    print('Starting new cycle! '+str(datetime.datetime.now())[0:-7]+'\n')
    browser = webdriver.Chrome(service=service, options=options)
    browser.set_window_size(1280, 720) 
    browser.delete_all_cookies()
    browser.get(url)
    time.sleep(5)
    for y in stops:
        print("______________________________\nСпирка: "+f"{y}")
        browser.find_element("xpath", "/html/body/div/main/div[1]/section/div/div[1]/div/div/div/div[3]/div/div[2]/label/input").click()
        browser.find_element("xpath", "/html/body/div/main/div[1]/section/div/div[1]/div/div/div/div[3]/div/div[2]/label/input").send_keys("\("f"{y}""\)")
        browser.find_element("xpath", "/html/body/div[1]/main/div[1]/section/div/div[1]/div/div/div[1]/div[3]/div/div[2]/ul").click()
        time.sleep(1)
        html = browser.page_source
        soup = BeautifulSoup(html.encode('utf-8'), 'html.parser')
        #print(soup)
        
        
        for i,div in enumerate(soup.find_all('div', {'class': 'grid grid-cols-2 st:grid-cols-6 gap-4 cursor-pointer py-2 items-center border-b'},limit = 16), start=total_i):
            #print(div)
            if "/bus.png" in str(div):
                type = "A"
                line = type+str(div.find_next('span', {'class': 'rounded-md w-14 h-7 text-white font-extrabold text-center flex flex-col justify-center'}).text)
            elif "/subway.png" in str(div):
                type = "M"
                if "h-7 w-7 flex items-center justify-center font-bold rounded text-base rounded-full text-black" in str(div):
                    line = type+str(div.find_next('span', {'class': 'h-7 w-7 flex items-center justify-center font-bold rounded text-base rounded-full text-black'}).text)
                else:
                    line = type+str(div.find_next('span', {'class': 'h-7 w-7 flex items-center justify-center font-bold rounded text-base rounded-full text-white'}).text)
            elif "/tram.png" in str(div):
                type = "T"
                line = type+str(div.find_next('span', {'class': 'rounded-md w-14 h-7 text-white font-extrabold text-center flex flex-col justify-center'}).text)
            elif "/trolley.png" in str(div):
                type = "TB"
                line = type+str(div.find_next('span', {'class': 'rounded-md w-14 h-7 text-white font-extrabold text-center flex flex-col justify-center'}).text)
            elif "/night_bus.png" in str(div):
                type = ""
                line = type+str(div.find_next('span', {'class': 'rounded-md w-14 h-7 text-white font-extrabold text-center flex flex-col justify-center'}).text)
            
            direction = str(div.find_next('h1', {'class': 'col-span-1 lg:col-span-3 2xl:col-span-4 font-bold text-xs lg:text-sm text-st-blue-dark'}).text.replace("   ","-").replace("(","").replace(")",""))
            direction_trans = direction.translate(table).replace(" ","_")
            globals()[f"topic{i}"] = f"homeassistant/sensor/sofiatraffic/{y}_"+line+"_"+direction_trans
            #print(f"Topic {i}: {globals()[f'topic{i}']}")
            if str(div).count("dash") < 3:
                if (("text-2xl") in str(div)):
                    line_arrival_times = str(div.find_next('span', {'class': 'text-2xl'}).text)
                    if (str(div).count("text-sm") >= 2) and ("мин" not in str(div.find_next('span', {'class': 'text-sm'}).text)):
                        line_arrival_times = line_arrival_times+", "+str(div.find_next('span', {'class': 'text-sm'}).text)
                        if str(div).count("text-sm") == 4:
                            line_arrival_times = line_arrival_times+", "+str(div.find_next('span', {'class': 'text-sm'}).find_next('span', {'class': 'text-sm'}).text)
            else:
                line_arrival_times = ""
            globals()[f"msg{i}"] = line_arrival_times
            #print(f"Message {i}: {globals()[f'msg{i}']}")
            print("Линия: "+line)
            print("Направление: "+direction)
            if line_arrival_times!="":
                print("Пристига след: "+line_arrival_times+' мин.'+'\n')
            else:
                print("Пристига след: Няма"+'\n')
            line = ""
            type = ""
            direction = ""
            line_arrival_times = ""
            total_i += 1
        browser.delete_all_cookies()
        browser.refresh()
        time.sleep(5)

    browser.close()
    browser.quit()

    def connect_mqtt():
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print("Connected to MQTT Broker!")
            else:
                print("Failed to connect, return code %d\n", rc)

        client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION1, client_id)
        client.username_pw_set(username, password)
        client.on_connect = on_connect
        client.connect(broker, port)
        return client

    def publish(client):
        for z in range(total_i):
            client.publish(globals()[f'topic{z}'], globals()[f'msg{z}'])
        

    def on_disconnect(client, userdata, rc):
        logging.info("Disconnected with result code: %s", rc)
        reconnect_count, reconnect_delay = 9, FIRST_RECONNECT_DELAY
        while reconnect_count < MAX_RECONNECT_COUNT:
            logging.info("Reconnecting in %d seconds...", reconnect_delay)
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                logging.info("Reconnected successfully!")
                return
            except Exception as err:
                logging.error("%s. Reconnect failed. Retrying...", err)

            reconnect_delay *= RECONNECT_RATE
            reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
            reconnect_count += 1
        logging.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)
        global FLAG_EXIT
        FLAG_EXIT = True

    def run():
        try:
            client = connect_mqtt()
            publish(client)
            client.on_disconnect = on_disconnect
        except:
            return

    if __name__ == '__main__':
        run()

    total_i = 0
    print('Cycle done! '+str(datetime.datetime.now())[0:-7]+'\n')
    print('Next cycle starts in '+str(freq)+' seconds.'+'\n\n\n')
    for i in range(freq):
        time.sleep(1)
