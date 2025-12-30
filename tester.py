import socket, random, threading, asyncio, time
from dataclasses import dataclass
import struct

class Client:
    def __init__(self, host_ip: str, port: int):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("", 480))
        self.server_ip = host_ip
        self.server_port = port

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
        self.sock.sendto(frame, (self.server_ip, self.server_port))

    def send_corrupted(self, payload: bytes):
        checksum = (self.crc32_from_bytes(payload) + 1) & 0xFFFFFFFF
        frame = payload + struct.pack("!I", checksum)
        self.sock.sendto(frame, (self.server_ip, self.server_port))

    def recv(self) :
        data = None
        data, addr = self.sock.recvfrom(65535)
        crc_bytes = data[-4:]
        x = data[:-4]
        header, token, timer = \
            struct.unpack("!BII", x)
        type = (header >> 6) & 0x3
        device_id = (header >> 4) & 0x3
        payload = {"type" :type,
                   "id" : device_id,
                   "token" : token,
                   "timer" : timer}
        to_return = {"payload" : payload,
                     "checksum": crc_bytes}
        return to_return


    def close(self):
        self.sock.close()
        print("Client closed..")

@dataclass
class Device:
    id : int
    token : int
    battery : bool
    not_send = False
    response : bool
    def __init__(self, id: int):
        self.id = id
        self.token = 0
        self.battery = False
        self.response = True
    def set_token(self, token: int):
        self.token = token
    def set_send(self):
        if not self.not_send:
            self.not_send = True
        else:
            self.not_send = False
    def send_getter(self) -> bool:
        return self.not_send
    def response_getter(self) -> bool:
        return self.response
    def response_setter(self, response: bool):
        self.response = response
    def to_json(self):
        return
    def register_json(self):
        low_battery = 0
        if self.battery:
            low_battery = 1
        type = 2
        id = self.id
        header = ((type & 0x3) << 6) \
                 | ((id & 0x3) << 4) \
                 | ((low_battery & 0x1) << 3)
        token = self.token
        timer = int(time.time())
        format_ch = "!BII"
        x = struct.pack(format_ch,
                        header,
                        token,
                        timer,
                        )
        return x

@dataclass
class ThermoNode(Device):
    temperature : float
    humidity : float
    dew_point : float
    pressure : float
    def __init__(self):
        super().__init__(0)
        self.temperature = round(random.uniform(-50.0, 60.0), 1)
        self.humidity = round(random.uniform(0.0, 100.0), 1)
        self.dew_point = round(random.uniform(-50.0, 60.0), 1)
        self.pressure = round(random.uniform(800.00,1100.00), 2)
    def to_json(self):
        low_battery = 0
        if self.battery:
            low_battery = 1
        type = 1
        id = 0
        header = ((type & 0x3) << 6) \
                | ((id   & 0x3) << 4) \
                | ((low_battery  & 0x1) << 3)
        token = self.token
        timer = int(time.time())
        temper = int(self.temperature * 10)#h
        humidity = int(self.humidity*10)#H
        dew_point = int(self.dew_point*10)#h
        pressure = int(self.pressure*100) - 80_000#-80_000, aby sa to vopachalo do 2 bajtov, na server side sa pricita 80 000 a vydeli 100 - H
        format_ch = "!BIIhHhH"
        x = struct.pack(format_ch,
                        header,
                        token,
                        timer,
                        temper,
                        humidity,
                        dew_point,
                        pressure)
        return x
    def change_temperature(self):
        bat = input("Is battery low?(y/n): ")
        temp_set = False
        hum_set = False
        dew_set = False
        pressure_set = False
        while not temp_set or not hum_set or not dew_set or not pressure_set:
            if temp_set == False:
                choice = input("Do you wish to set the temperature? (y/n): ")
                if choice == "y":
                    number = input("Enter temperature <-50.0 - 60.0> 1 decimal value: ")
                    temp_set = True
                    temperature = float(number)
            if hum_set == False:
                choice = input("Do you wish to set the humidity? (y/n): ")
                if choice == "y":
                    number = input("Enter humidity <0.0 - 100.0> 1 decimal value: ")
                    hum_set = True
                    humidity = float(number)
            if dew_set == False:
                choice = input("Do you wish to set the dew point? (y/n): ")
                if choice == "y":
                    number = input("Enter dew point <-50.0 - 60.0> 1 decimal value: ")
                    dew_set = True
                    dew_point = float(number)
            if pressure_set == False:
                choice = input("Do you wish to set the pressure? (y/n): ")
                if choice == "y":
                    number = input("Enter pressure <800.00 - 1100.00> 2 decimal values: ")
                    pressure_set = True
                    pressure = float(number)
        self.temperature = temperature
        self.humidity = humidity
        self.dew_point = dew_point
        self.pressure = pressure
        if bat == "y":
            self.battery = True



@dataclass
class WindSense(Device):
    wind_speed : float
    wind_gust : float
    wind_direction : int
    turbulence : float
    def __init__(self):
        super().__init__(1)
        self.wind_speed = round(random.uniform(0.0, 50.0), 1)
        self.wind_gust = round(random.uniform(0.0, 70.0), 1)
        self.wind_direction = random.randint(0, 359)
        self.turbulence = round(random.uniform(0.0, 1.0), 1)
    def to_json(self):
        low_battery = 0
        if self.battery:
            low_battery = 1
        type = 1
        id = 1
        header = ((type & 0x3) << 6) \
                 | ((id & 0x3) << 4) \
                 | ((low_battery & 0x1) << 3)
        token = self.token
        timer = int(time.time())
        wind_speed = int(self.wind_speed * 10)#H
        wind_gust = int(self.wind_gust * 10)#H
        wind_direction = self.wind_direction
        turbulence = int(self.turbulence * 10)
        combined = ((wind_direction & 0x1FF) << 7) | ((turbulence & 0xF) << 3)
        format_ch = "!BIIHHH"
        x = struct.pack(format_ch,
                        header,
                        token,
                        timer,
                        wind_speed,
                        wind_gust,
                        combined
                        )
        return x
    def change_wind(self):
        bat = input("Is battery low?(y/n): ")
        speed_set = False
        gust_set = False
        direction_set = False
        turbulence_set = False
        while not speed_set or not gust_set or not direction_set or not turbulence_set:
            if speed_set == False:
                choice = input("Do you wish to set the speed? (y/n): ")
                if choice == "y":
                    number = input("Enter speed <0.0 - 50.0> 1 decimal value: ")
                    speed_set = True
                    wind_speed = float(number)
            if gust_set == False:
                choice = input("Do you wish to set the gust? (y/n): ")
                if choice == "y":
                    number = input("Enter gust <0.0 - 70.0> 1 decimal value: ")
                    gust_set = True
                    wind_gust = float(number)
            if direction_set == False:
                choice = input("Do you wish to set the direction? (y/n): ")
                if choice == "y":
                    number = input("Enter direction <0-359> 0 decimal values: ")
                    direction_set = True
                    wind_direction = int(number)
            if turbulence_set == False:
                choice = input("Do you wish to set the turbulence? (y/n): ")
                if choice == "y":
                    number = input("Enter turbulence <0.0 - 1.0> 1 decimal value: ")
                    turbulence_set = True
                    turbulence = float(number)
        self.wind_speed = wind_speed
        self.wind_gust = wind_gust
        self.wind_direction = wind_direction
        self.turbulence = turbulence
        if bat == "y":
            self.battery = True


@dataclass
class RainDetect(Device):
    rainfall : float
    soil_moisture : float
    flood_risk: int
    rain_duration : int
    def __init__(self):
        super().__init__(2)
        self.rainfall = round(random.uniform(0.0, 500.0), 1)
        self.soil_moisture = round(random.uniform(0.0, 100.0), 1)
        self.flood_risk = random.randint(0,4)
        self.rain_duration = random.randint(0,60)
    def to_json(self):
        low_battery = 0
        if self.battery:
            low_battery = 1
        type = 1
        id = 2
        header = ((type & 0x3) << 6) \
                 | ((id & 0x3) << 4) \
                 | ((low_battery & 0x1) << 3)
        token = self.token
        timer = int(time.time())
        rainfall = int(self.rainfall * 10)
        soil_moisture = int(self.soil_moisture * 10)#H
        flood_risk = self.flood_risk
        rain_duration = self.rain_duration#B
        combined = (rainfall << 3) | (flood_risk & 0x7)#H
        format_ch = "!BIIHBH"
        x = struct.pack(format_ch,
                        header,
                        token,
                        timer,
                        soil_moisture,
                        rain_duration,
                        combined
                        )
        return x
    def change_rain(self):
        bat = input("Is battery low?(y/n): ")
        rainfall_set = False
        moisture_set = False
        risk_set = False
        duration_set = False
        while not rainfall_set or not moisture_set or not risk_set or not duration_set:
            if rainfall_set == False:
                choice = input("Do you wish to set the rainfall? (y/n): ")
                if choice == "y":
                    number = input("Enter rainfall <0.0 - 500.0> 1 decimal value: ")
                    rainfall_set = True
                    rainfall = float(number)
            if moisture_set == False:
                choice = input("Do you wish to set the moisture? (y/n): ")
                if choice == "y":
                    number = input("Enter moisture <0.0 - 100.0> 1 decimal value: ")
                    moisture_set = True
                    moisture = float(number)
            if risk_set == False:
                choice = input("Do you wish to set the risk? (y/n): ")
                if choice == "y":
                    number = input("Enter risk <0/1/2/3/4> 0 decimal values: ")
                    risk_set = True
                    risk = int(number)
            if duration_set == False:
                choice = input("Do you wish to set the duration? (y/n): ")
                if choice == "y":
                    number = input("Enter duration <0-60> 0 decimal values: ")
                    duration_set = True
                    duration = int(number)
        self.rainfall = rainfall
        self.soil_moisture = moisture
        self.flood_risk = risk
        self.rain_duration = duration
        if bat == "y":
            self.battery = True


@dataclass
class AirQualityBox(Device):
    co2 : int
    ozone : float
    AQI : int
    def __init__(self):
        super().__init__(3)
        self.co2 = random.randint(300,5000)
        self.ozone = round(random.uniform(0.0, 500.0), 1)
        self.AQI = random.randint(0,500)

    def to_json(self):
        low_battery = 0
        if self.battery:
            low_battery = 1
        type = 1
        id = 3
        header = ((type & 0x3) << 6) \
                 | ((id & 0x3) << 4) \
                 | ((low_battery & 0x1) << 3)
        token = self.token
        timer = int(time.time())
        co2 = self.co2#H
        ozone = int(self.ozone*10)#H
        AQI = self.AQI#H

        format_ch = "!BIIHHH"
        x = struct.pack(format_ch,
                        header,
                        token,
                        timer,
                        co2,
                        ozone,
                        AQI
                        )
        return x
    def change_airquality(self):
        bat = input("Is battery low?(y/n): ")
        c02_set = False
        ozone_set = False
        AQI_set = False
        while not c02_set or not ozone_set or not AQI_set:
            if c02_set == False:
                choice = input("Do you wish to set the c02? (y/n): ")
                if choice == "y":
                    number = input("Enter c02 <300 - 5000> 0 decimal values: ")
                    c02_set = True
                    c2 = int(number)
            if ozone_set == False:
                choice = input("Do you wish to set the ozone? (y/n): ")
                if choice == "y":
                    number = input("Enter ozone <0.0 - 500.0> 1 decimal value: ")
                    ozone_set = True
                    ozone = float(number)
            if AQI_set == False:
                choice = input("Do you wish to set the AQI? (y/n): ")
                if choice == "y":
                    number = input("Enter AQI <0 - 500> 0 decimal values: ")
                    AQI_set = True
                    AQI = int(number)
        self.AQI = AQI
        self.co2 = c2
        self.ozone = ozone
        if bat == "y":
            self.battery = True



def listener(client: Client, thermo: ThermoNode, wind: WindSense, air: AirQualityBox, rain: RainDetect):
    no_therm, no_wind, no_air, no_rain = 0,0,0,0
    while True:
        data = client.recv()
        if "payload" in data:
            data = data["payload"]
            if data["type"] == 1:
                if data["id"] == 0:
                    thermo.set_token(data["token"])
                elif data["id"] == 1:
                    wind.set_token(data["token"])
                elif data["id"] == 2:
                    rain.set_token(data["token"])
                elif data["id"] == 3:
                    air.set_token(data["token"])
            elif data["type"] == 0:
                if data["id"] == 0:
                    thermo.response_setter(True)
                elif data["id"] == 1:
                    wind.response_setter(True)
                elif data["id"] == 2:
                    rain.response_setter(True)
                elif data["id"] == 3:
                    air.response_setter(True)
            elif data["type"] == 3:
                if data["id"] == 0:
                    client.send(thermo.to_json())
                elif data["id"] == 1:
                    client.send(wind.to_json())
                elif data["id"] == 2:
                    client.send(rain.to_json())
                elif data["id"] == 3:
                    client.send(air.to_json())
            elif data["type"] == 2:
                if data["id"] == 0:
                    no_therm += 1
                    if no_therm == 3:
                        thermo.set_send()
                        client.send(thermo.to_json())
                        no_therm = 0
                elif data["id"] == 1:
                    no_wind += 1
                    if no_wind == 3:
                        wind.set_send()
                        client.send(wind.to_json())
                        no_wind = 0
                elif data["id"] == 2:
                    no_rain += 1
                    if no_rain == 3:
                        rain.set_send()
                        client.send(rain.to_json())
                        no_rain = 0
                elif data["id"] == 3:
                    no_air += 1
                    if no_air == 3:
                        air.set_send()
                        client.send(air.to_json())
                        no_air = 0

async def monitoring(client: Client, device : Device):
    await asyncio.sleep(1)
    while not device.response_getter():
        client.send(device.to_json())
        await asyncio.sleep(1)


async def sender(client : Client, thermo : ThermoNode, wind : WindSense, air : AirQualityBox, rain : RainDetect ):
    while True:
        await asyncio.sleep(10)
        if not thermo.send_getter() and thermo.response_getter():
            client.send(thermo.to_json())
            thermo.response_setter(False)
            asyncio.create_task(monitoring(client, thermo))
        if not wind.send_getter() and wind.response_getter():
            client.send(wind.to_json())
            wind.response_setter(False)
            asyncio.create_task(monitoring(client, wind))
        if not rain.send_getter() and  rain.response_getter():
            client.send(rain.to_json())
            rain.response_setter(False)
            asyncio.create_task(monitoring(client, rain))
        if not air.send_getter() and air.response_getter():
            client.send(air.to_json())
            air.response_setter(False)
            asyncio.create_task(monitoring(client, air))


def runner(client : Client, thermo : Device, wind : Device, rain : Device, air : Device):
    asyncio.run(sender(client, thermo, wind, rain, air,))



if __name__=="__main__":
    print("Client starting..")
    print("Type configure to configure (UAT_1), type change to UAT_2,\n"
          " type corrupt to UAT_3,type check to UAT_4, type exit to exit")
    thermo = ThermoNode()
    wind = WindSense()
    air = AirQualityBox()
    rain = RainDetect()
    command = "haha"
    while command != "exit":
        command = input("Menu: ")
        if command == "configure":
            ip = input("Server ip: ")
            port = int(input("Server port (dal som tam 490): "))
            client = Client( ip, port)
            t1 = threading.Thread(target=listener, args=(client, thermo, wind, air, rain))
            t1.start()
            client.send(thermo.register_json())
            client.send(wind.register_json())
            client.send(rain.register_json())
            client.send(air.register_json())
            t2 = threading.Thread(target=runner, args=(client, thermo, wind, air, rain))
            t2.start()
        elif command == "change":
            choice = input("Choose temp/wind/rain/air: ")
            if choice == "temp":
                thermo.change_temperature()
                client.send(thermo.to_json())
            elif choice == "wind":
                wind.change_wind()
                client.send(wind.to_json())
            elif choice == "rain":
                rain.change_rain()
                client.send(rain.to_json())
            elif choice == "air":
                air.change_airquality()
                client.send(air.to_json())
        elif command == "corrupt":
            choice = input("Choose temp/wind/rain/air: ")
            if choice == "temp":
                client.send_corrupted(thermo.to_json())
            elif choice == "wind":
                client.send_corrupted(wind.to_json())
            elif choice == "rain":
                client.send_corrupted(rain.to_json())
            elif choice == "air":
                client.send_corrupted(air.to_json())
        elif command == "check":
            choice = input("Choose temp/wind/rain/air: ")
            if choice == "temp":
                thermo.set_send()
            elif choice == "wind":
                wind.set_send()
            elif choice == "rain":
                rain.set_send()
            elif choice == "air":
                air.set_send()
        elif command == "exit":
            break
        else:
            print("Invalid command")
    client.close()