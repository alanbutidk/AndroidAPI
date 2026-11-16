from AndroidAPI import DeviceInfo, DevicePower, OpenApp, AndroidInfo
from AdbConnect import AdbUsbConnect
from time import sleep

print("\033[31mMake sure to connect to USB before executing!\033[0m")
input("Press enter when you have connected your device")

conn = AdbUsbConnect()
print(DeviceInfo(conn).GetDeviceInfo())

info = AndroidInfo(conn)
info.AndroidVersion(say=True)
info.AndroidSDKVersion(say=True)
info.AndroidBuildID(say=True)

app = OpenApp(conn)
app.Open("com.android.chrome")
sleep(10)
app.Close("com.android.chrome")

conn.close()
