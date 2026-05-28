from AndroidAPI import DeviceInfo, DevicePower, OpenApp, AndroidInfo, SideloadAPK
from AdbConnect import AdbUsbConnect

import os;os.system("")

print("\x1b[31mMake sure to connect to USB before executing!\033[0m")
input("Press enter when you have connected your device")

conn = AdbUsbConnect()
print(DeviceInfo.GetDeviceInfo(conn))

AndroidInfo.AndroidVersion(conn, say=True)
AndroidInfo.AndroidSDKVersion(conn, say=True)
AndroidInfo.AndroidBuildID(conn, say=True)

OpenApp.Open(conn, "com.android.chrome")
OpenApp.Close(conn, "com.android.chrome")

a = input("Please enter yes or no to shutdown device: ")
if a.lower == "yes":
    DevicePower.Shutdown(conn, "graceful")
else:
    pass

conn.close()
