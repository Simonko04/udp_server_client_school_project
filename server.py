import asyncio
import socket,  random, time
import threading
from dataclasses import dataclass
import struct


tokens = {0 : 0,
          1 : 0,
          2 : 0,
          3 : 0}

@dataclass
class Server:
    typing: bool
    thermo_supress : bool
    wind_supress : bool
    rain_supress : bool
    air_supress : bool
    no_thermo : int
    no_wind : int
    no_rain : int
    no_air : int
    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 490))
        self.typing = True
        self.thermo_supress, self.wind_supress, self.rain_supress, self.air_supress = False,False,False,False
        self.no_thermo, self.no_wind, self.no_rain, self.no_air = 0,0,0,0

    def crc32_from_bytes(self, data: bytes) -> int:
        crc = 0xFFFFFFFF
        poly = 0xEDB88320
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 1:
                    crc = (crc >> 1) ^ poly
                else:
                    crc >>= 1
        return crc ^ 0xFFFFFFFF

    def send(self, payload: bytes):
        checksum = self.crc32_from_bytes(payload)
        frame = payload + struct.pack("!I", checksum)
        self.sock.sendto(frame, (self.client))

    def recv(self):
        data = None
        data, self.client = self.sock.recvfrom(65535)
        crc_bytes = data[-4:]
        x = data[:-4]
        header = x[0]
        type = (header >> 6) & 0x3  # bity 7–6
        device_id = (header >> 4) & 0x3  # bity 5–4
        low_battery = (header >> 3) & 0x1  # bit 3
        if type == 2:
            header,token, timer  = \
            struct.unpack("!BII", x)
            payload = {"type":type,
                       "id":device_id,
                       "token":token,
                       "timestamp":timer,
                       "low_battery":low_battery}
        elif device_id == 0:#temp
            header, token, timer, temper, humid, dew, press = \
                struct.unpack("!BIIhHhH", x)
            temper = float(temper)/10
            humid = float(humid)/10
            dew = float(dew)/10
            press = (float(press)/100) + 800
            payload = {"type": type,
                        "id" : device_id,
                       "token" : token,
                       "timestamp" : timer,
                       "battery" : low_battery,
                       "temperature" : temper,
                       "humidity" : humid,
                       "dew_point" : dew,
                       "pressure" : press
                       }

        elif device_id == 1:  # WindSense
                header, token, timer, ws, wg, combined = \
                    struct.unpack("!BIIHHH", x)
                wind_direction = (combined >> 7) & 0x1FF
                turb = (combined >> 3) & 0xF
                ws = float(ws)/10
                wg = float(wg)/10
                turb = float(turb)/10
                payload = {"type": type,
                           "id": device_id,
                           "token": token,
                           "timestamp": timer,
                           "battery": low_battery,
                           "wind_speed" : ws,
                           "wind_gust" : wg,
                           "wind_direction" : wind_direction,
                           "turbulence" : turb
                           }

        elif device_id == 2:#rain
            header, token, timer, soil_m, rain_dur, combined = \
                struct.unpack("!BIIHBH", x)
            rainfall = combined >> 3
            flood_risk = combined & 0x7
            rainfall = float(rainfall)/10
            soil_m = float(soil_m)/10
            payload = {"type": type,
                       "id": device_id,
                       "token": token,
                       "timestamp": timer,
                       "battery": low_battery,
                       "rainfall" : rainfall,
                       "soil_moisture" : soil_m,
                       "flood_risk" : flood_risk,
                       "rain_duration" : rain_dur,
                       }


        elif device_id == 3:  # AirQualityBox
                header, token, timer, co2, ozone, aqi = \
                    struct.unpack("!BIIHHH", x)
                ozone = float(ozone)/10
                payload = {"type": type,
                           "id": device_id,
                           "token": token,
                           "timestamp": timer,
                           "battery": low_battery,
                           "co2" : co2,
                           "ozone" : ozone,
                           "AQI" : aqi
                           }

        to_return = {"payload" : payload,
                     "checksum" : crc_bytes}

        return to_return, x

    def close(self):
        self.sock.close()
        print("Sever closed..")
    def typing_getter(self) -> bool:
        return self.typing
    def typing_setter(self, command : bool) -> None:
        self.typing = command
    def supress_setter(self, word : str, command: bool) -> None:
        if word == 'thermo':
            self.thermo_supress = command
        elif word == "wind":
            self.wind_supress = command
        elif word == "rain":
            self.rain_supress = command
        elif word == "air":
            self.air_supress = command
    def supress_getter(self, word : str) -> bool:
        if word == 'thermo':
            return self.thermo_supress
        elif word == 'wind':
            return self.wind_supress
        elif word == 'rain':
            return self.rain_supress
        elif word == 'air':
            return self.air_supress
    def no_setter(self, word : str, number: int) -> None:
        if word == 'thermo':
            self.no_thermo = number
        elif word == "wind":
            self.no_wind = number
        elif word == "rain":
            self.no_rain = number
        elif word == "air":
            self.no_air = number
    def no_getter(self, word:str) -> int:
        if word == 'thermo':
            return self.no_thermo
        elif word == 'wind':
            return self.no_wind
        elif word == 'rain':
            return self.no_rain
        elif word == 'air':
            return self.no_air


def server_registration(ID, oldtoken):
    token =  random.randint(1, 2147483647)
    if oldtoken != 0:
        return 0
    if ID == 0:
        tokens[0] = token
    elif ID == 1:
        tokens[1] = token
    elif ID == 3:
        tokens[3] = token
    elif ID == 2:
        tokens[2] = token
    else:
        return 0
    return token

def registration(data, server : Server):
    token = server_registration(data["id"], data["token"])

    if token == 0:
        return
    type = 1  # 1 = reg_ack
    id = data["id"]
    header = ((type & 0x3) << 6) \
             | ((id & 0x3) << 4)

    token = token  # I
    timer = int(time.time())  # I
    format_ch = "!BII"
    x = struct.pack(format_ch,
                    header,
                    token,
                    timer)
    print("INFO: ", str(data["id"]), "REGISTERED at", str(data["timestamp"]) + '.')
    server.send(x)


def informer(data, server : Server):
    type = 0  # 0 = info_ack
    id = data["id"]
    header = ((type & 0x3) << 6) \
             | ((id & 0x3) << 4)

    token = data["token"]  # I
    timer = int(time.time())  # I
    format_ch = "!BII"
    x = struct.pack(format_ch,
                    header,
                    token,
                    timer)
    if data["id"] == 0 and data["token"] == tokens[0]:
        if not data["battery"] and server.typing_getter():
            print(str(data["timestamp"]),'-', str(data["id"]), "\n" +
                  "temperature:", str(data["temperature"])+';' +
                  "humidity:", str(data["humidity"])+';' +
                  "dew_point:", str(data["dew_point"])+';' +
                  "pressure:", str(data["pressure"])+';', "\n")
        elif server.typing_getter():
            print(str(data["timestamp"]),'-',"WARNING: LOW BATTERY", str(data["id"]), '\n' +
                  "temperature:", str(data["temperature"])+';' +
                  "humidity:", str(data["humidity"])+';' +
                  "dew_point:", str(data["dew_point"])+';' +
                  "pressure:", str(data["pressure"])+';', "\n")
        if not server.supress_getter("thermo"):
            server.send(x)
        elif server.no_getter("thermo") == 3:
            server.send(x)
            server.no_setter("thermo", 0)
            server.supress_setter("thermo", False)
        else:
            server.no_setter("thermo", server.no_getter("thermo") + 1)
    elif data["id"] == 1 and data["token"] == tokens[1]:
        if not data["battery"] and server.typing_getter():
            print(str(data["timestamp"]),'-', str(data["id"]), '\n' +
                  "wind_speed:", str(data["wind_speed"])+';' +
                  "wind_gust:", str(data["wind_gust"])+';' +
                  "wind_direction:", str(data["wind_direction"])+';' +
                  "turbulence:", str(data["turbulence"])+';', "\n")
        elif server.typing_getter():
            print(str(data["timestamp"]),'-',"WARNING: LOW BATTERY", str(data["id"]), '\n' +
                  "wind_speed:", str(data["wind_speed"])+';' +
                  "wind_gust:", str(data["wind_gust"])+';' +
                  "wind_direction:", str(data["wind_direction"])+';' +
                  "turbulence:", str(data["turbulence"])+';', "\n")
        if not server.supress_getter("wind"):
            server.send(x)
        elif server.no_getter("wind") == 3:
            server.send(x)
            server.no_setter("wind", 0)
            server.supress_setter("wind", False)
        else:
            server.no_setter("wind", server.no_getter("wind") + 1)
    elif data["id"] == 2 and data["token"] == tokens[2]:
        if not data["battery"] and server.typing_getter():
            print(str(data["timestamp"]),'-', str(data["id"]), '\n' +
                  "rainfall:", str(data["rainfall"])+';' +
                  "soil_moisture:", str(data["soil_moisture"])+';' +
                  "flood_risk:", str(data["flood_risk"])+';' +
                  "rain_duration:", str(data["rain_duration"])+';', "\n")
        elif server.typing_getter():
            print(str(data["timestamp"]),'-',"WARNING: LOW BATTERY", str(data["id"]), '\n' +
                  "rainfall:", str(data["rainfall"])+';' +
                  "soil_moisture:", str(data["soil_moisture"])+';' +
                  "flood_risk:", str(data["flood_risk"])+';' +
                  "rain_duration:", str(data["rain_duration"])+';', "\n")
        if not server.supress_getter("rain"):
            server.send(x)
        elif server.no_getter("rain") == 3:
            server.send(x)
            server.no_setter("rain", 0)
            server.supress_setter("rain", False)
        else:
            server.no_setter("rain", server.no_getter("rain") + 1)

    elif data["id"] == 3 and data["token"] == tokens[3]:
        if not data["battery"] and server.typing_getter():
            print(str(data["timestamp"]),'-', str(data["id"]), '\n' +
                    "co2:", str(data["co2"])+';' +
                    "ozone:", str(data["ozone"])+';' +
                    "AQI:", str(data["AQI"])+';', "\n")
        elif server.typing_getter():
            print(str(data["timestamp"]),'-',"WARNING: LOW BATTERY", str(data["id"]), '\n' +
                "co2:", str(data["co2"])+';' +
                "ozone:", str(data["ozone"])+';' +
                "AQI:", str(data["AQI"])+';', "\n")
        if not server.supress_getter("air"):
            server.send(x)
        elif server.no_getter("air") == 3:
            server.send(x)
            server.no_setter("air", 0)
            server.supress_setter("air", False)
        else:
            server.no_setter("air", server.no_getter("air") + 1)



def checksum_tester(data, checksum, server : Server) -> bool:
    recv_crc, = struct.unpack("!I", checksum)
    new_checksum = server.crc32_from_bytes(data)
    if new_checksum == recv_crc:
        return True
    else:
        return False


async def monitoring(data, server: Server, client_state):
    disconnected = False
    device_id = data["id"]
    try:
        while True:
            await asyncio.sleep(15)

            last_seen = client_state[data["id"]]["last_seen"]

            if (asyncio.get_event_loop().time() - last_seen) < 15:
                continue

            type = 2# 2 = idle
            id = data["id"]
            header = ((type & 0x3) << 6) \
                     | ((id & 0x3) << 4)

            token = data["token"]#I
            timer = int(time.time())#I
            format_ch = "!BII"
            x = struct.pack(format_ch,
                            header,
                            token,
                            timer)
            server.send(x)
            await asyncio.sleep(1)
            if server.typing_getter():
                print(f"WARNING: {device_id} DISCONNECTED!\n")
            disconnected = True
            await asyncio.sleep(1)

            if (asyncio.get_event_loop().time() - client_state[data["id"]]['last_seen']) >= 1:
                for i in range(9):
                    if (asyncio.get_event_loop().time() - client_state[data["id"]]['last_seen']) < 1 and server.typing_getter():
                        if server.typing_getter():
                            print(f"INFO: {device_id} RECONNECTED!\n")
                        break
                    else:
                        await asyncio.sleep(4)
                        server.send(x)
                    await asyncio.sleep(1)
                    if server.typing_getter():
                        print(f"WARNING: {device_id} DISCONNECTED!\n")

    except asyncio.CancelledError:
        if disconnected == True:
            if server.typing_getter():
                print(f"INFO: Device {device_id} RECONNECTED!\n")
        pass


async def listener(server : Server):
    loop = asyncio.get_event_loop()
    client_state = {}
    while True:
        data, x = await loop.run_in_executor(None, server.recv)
        if "payload" in data:
            new_data = data["payload"]
            if checksum_tester(x, data["checksum"], server):
                if new_data["type"] == 2:
                    registration(new_data, server)
                elif new_data["type"] == 1:
                    if new_data["id"] not in client_state:
                        client_state[new_data["id"]] = {}
                    client_state[new_data["id"]]['last_seen'] = loop.time()
                    if client_state[new_data["id"]].get("task"):
                        client_state[new_data["id"]]["task"].cancel()
                    client_state[new_data["id"]]["task"] = asyncio.create_task(
                        monitoring(new_data, server, client_state))
                    informer(new_data, server)
            else:
                type = 3  # 3 = corrupted
                id = new_data["id"]
                header = ((type & 0x3) << 6) \
                         | ((id & 0x3) << 4)

                token = new_data["token"]  # I
                timer = int(time.time())  # I
                format_ch = "!BII"
                x = struct.pack(format_ch,
                                header,
                                token,
                                timer)
                if server.typing_getter():
                    print("INFO: ", str(new_data["id"]), "CORRUPTED DATA at", str(new_data["timestamp"])+'.', 'REQUESTING DATA')
                server.send(x)

def runner(server:Server):
    asyncio.run(listener(server))


if __name__=="__main__":
    print("Server starting..")
    print("Type configure to configure, press ENTER to stop printing and type in a command, type exit to exit")
    data = "empty"
    command = "empty"
    server = None
    while command != "exit":
        print("type ignore to test UAT_5")
        command = input("Menu: ")
        if command == "configure":
            server = Server()
            t1 = threading.Thread(target=runner, args=(server,))
            t1.start()
        elif command == "ignore":
            if server == None:
                print("Must configure first \n")
            else:
                choice = input("Choose temp/wind/rain/air: ")
                if choice == "temp":
                    server.supress_setter("thermo", True)
                elif choice == "wind":
                    server.supress_setter("wind", True)
                elif choice == "rain":
                    server.supress_setter("rain", True)
                elif choice == "air":
                    server.supress_setter("air", True)
        server.typing_setter(True)
        input()
        server.typing_setter(False)
    server.close()