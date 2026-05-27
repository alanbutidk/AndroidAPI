from AndroidAPI import DeviceInfo, DevicePower, OpenApp, AndroidInfo, SideloadAPK

ADBPath = str(input("Path to ADB: "))
FastbootPath = str(input("Path to fastboot: "))

print("=== Device State ===")
state = DeviceInfo.GetDeviceInfo(ADBPath, FastbootPath)
print(f"Current state: {state}")

print("\n=== Match States ===")
match = DeviceInfo._match_states(ADBPath, FastbootPath, "recovery")
if match is not None:
    print(match)
else:
    print("Device is not in recovery")

print("\n=== Android Info ===")
AndroidInfo.AndroidVersion(ADBPath, say=True)
AndroidInfo.AndroidSDKVersion(ADBPath, say=True)
AndroidInfo.AndroidBuildID(ADBPath, say=True)

print("\n=== Open App ===")
OpenApp.Open(ADBPath, "com.android.chrome")

import time
time.sleep(3)

print("\n=== Close App ===")
OpenApp.Close(ADBPath, "com.android.chrome")

print("\n=== Sideload APK ===")
SideloadAPK.SideloadAPK(ADBPath, "/home/user/Downloads/myapp.apk")

print("\n=== Shutdown (graceful) ===")
DevicePower.Shutdown(ADBPath, "graceful")