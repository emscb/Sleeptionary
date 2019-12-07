import sqlite3
import time
import Adafruit_DHT
import matplotlib as mpl
import pylab as plb
from Adafruit_AMG88xx import Adafruit_AMG88xx
import RPi.GPIO as GPIO


def db_insert(li, qr):
    value = tuple(li)
    rm = c.execute(qr, value)
    conn.commit()
    print("Data inserted.")


def tmhd():
    humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

    if humidity is not None and temperature is not None:
        print("Temp = %.1f'C    Humidity = %.1f%%" % (temperature, humidity))
    else:
        print('Failed to get reading. Try again!')

    query = '''INSERT INTO tmhd(TM, HD) VALUES(?,?)'''

    return [[temperature, humidity], query]


def lux():
    # TODO 조도 측정 코드
    lx = 0  # 조도값
    query = '''INSERT INTO lux(LX) VALUES(?)'''

    return [[lx], query]


# Connect database
db_path = "./test.db"
try:
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    print("DB connected.")
except sqlite3.OperationalError:
    print("There is no database in path.")

# Initialize DHT sensor
sensor = Adafruit_DHT.DHT11
pin = 4
print("Thermometer initialized.")

# Initialize thermal camera
camera = Adafruit_AMG88xx()
print("Thermal camera initialized.")

# Initialize button
GPIO.setmode(GPIO.BOARD)
GPIO.setup(15, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)
# GPIO.setup(16, GPIO.IN, pull_up_down=GPIO.PUD_UP)
print("Buttons initialized.")

# Standard time
standard_time = time.time()
t1 = time.localtime(standard_time)
started = True  # Sleep started
starttime = '%04d-%02d-%02d %02d:%02d:%02d' % (t1.tm_year, t1.tm_mon, t1.tm_mday, t1.tm_hour, t1.tm_min, t1.tm_sec)
ts = []  # Save temperatures
got_avg = False  # if got average temperature
while 1:
    t = time.time()

    # Check switches
    b1 = GPIO.input(15)
    # b2 = GPIO.input(18)
    # b3 = GPIO.input(16)
    if not b1:
        tag = 1
        print("Finish sleeping")
        break
    # elif not b2:
    #     tag = 0
    #     print("Slept soso.")
    #     break
    # elif not b3:
    #     tag = -1
    #     print("Bad sleep.")
    #     break

    # 5초 간격
    if int(standard_time - t) % 5 == 0:
        # 온습도 저장
        tmhd_vq = tmhd()
        db_insert(tmhd_vq[0], tmhd_vq[1])

        # 조도 저장
        lx_vq = lux()
        db_insert(lx_vq[0], lx_vq[1])

    # 2초 간격
    if int(standard_time - t) % 2 == 0:
        temps = camera.readPixels()
        temp = max(temps)
        ts.append(temp)
        # 기준 온도 저장 (ts[0])
        if len(ts) == 3 and not got_avg:
            avg_tm = (ts[0] + ts[1] + ts[2]) / 3
            ts = []
            ts.append(avg_tm)
            got_avg = True
        # 5분 동인 기준 온도보다 1.5도 떨어진 상태로 유지되면 and !started
        if not started:
            i = 0
            for f in ts[-5:]:
                if abs(ts[0] - f) < 1:
                    i += 1
                    continue
                else:
                    break
            if i == 5:
                t = time.localtime()
                starttime = '%04d-%02d-%02d %02d:%02d:%02d'\
                            % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)
                started = True

t = time.localtime()
endtime = '%04d-%02d-%02d %02d:%02d:%02d' % (t.tm_year, t.tm_mon, t.tm_mday, t.tm_hour, t.tm_min, t.tm_sec)

# 평균 온습도, 조도 계산
avg_TM_HD = c.execute('''SELECT avg(TM), avg(HD) FROM tmhd WHERE Timestamp BETWEEN "%s" and "%s"'''\
                      % (starttime, endtime)).fetchone()
print("avg_TM_HD : ")
print(avg_TM_HD)
avg_LX = c.execute('''SELECT avg(LX) FROM lux WHERE Timestamp BETWEEN "%s" and "%s"'''\
                   % (starttime, endtime)).fetchone()
print("avg_LX : ")
print(avg_LX)

# 저장
date = '%04d-%02d-%02d' % (t.tm_year, t.tm_mon, time.localtime(time.time() - 86400).tm_mday)
db_insert([date, starttime, endtime, avg_TM_HD[0], avg_TM_HD[1],
           avg_LX[0], tag], '''INSERT INTO Sleeptionary VALUES(?,?,?,?,?,?,?)''')

# TODO 그래프 그리기


conn.close()
GPIO.cleanup()
