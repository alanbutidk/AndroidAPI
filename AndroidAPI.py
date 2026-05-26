import subprocess as s
import sys
from pathlib import Path
import os

#Not considered a main class, RATHER helper classes!
class DeviceInfo:
    @staticmethod
    #Give device info -> return, usage: a = GetDeviceInfo()
    def GetDeviceInfo():
        adb = s.run(["adb", "get-state"], capture_output=True, text=True)
        if adb.returncode == 0:
            state = adb.stdout.strip()
            if state == "device":
                return "Normal"
            elif state == "recovery" or state == "sideload":
                return "Recovery"
        fastboot = s.run(["fastboot", "getvar", "current-slot"], capture_output=True, text=True)
        if fastboot.returncode == 0:
            combined = (fastboot.stdout + fastboot.stderr).lower()
            if "fastbootd" in combined:
                    return "fastbootd"
            return "bootloader"

        return "Unknown"
    @staticmethod
    #match device state with argument state, usage: a = _match_states("MyState!")
    def _match_states(State: str) -> str:
        match_func = DeviceInfo.GetDeviceInfo()
        if match_func == "Normal" and State.lower() == "system":
            return f"Trying to get to {State} but on {match_func}!"
        elif match_func == "fastbootd" and State.lower() == "fastbootd":
            return f"Trying to get to {State} but on {match_func}!"
        elif match_func == "Recovery" and State.lower() == "recovery":
            return f"Trying to get to {State} but on {match_func}!"
        elif match_func == "bootloader" and State.lower() == "bootloader":
            return f"Trying to get to {State} but on {match_func}!"
        else:
            return None
#Main classes--------------------------------------------------------
class DevicePower:
    #RebootTo -> ADBPath, 'reboot', State
    @staticmethod
    def RebootTo(ADBPath: str, State: str) -> str:
        ADBP = Path(ADBPath)
        if ADBP.exists():
            pass
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\033[0m")
            sys.exit(1)
        a = DeviceInfo.GetDeviceInfo()
        b = DeviceInfo._match_states(State)
        if b is not None:
            print(f"\x1b[31m{b}\033[0m")
            sys.exit(1)
        
        if State.lower() == "system":
            s.run([ADBPath, "reboot"])
        elif State.lower() == "recovery":
            s.run([ADBPath, "reboot", "recovery"])
        elif State.lower() == "fastbootd":
            s.run([ADBPath, "reboot", "fastboot"])
        elif State.lower() == "bootloader":
            s.run([ADBPath, "reboot", "bootloader"])
        else:
            print(f"\x1b[31mUnknown state: {State}\x1b[0m")
            sys.exit(1)
    #Shutdown, ADBPath, graceful/force -> adb shell 'cmd'
    @staticmethod
    def Shutdown(ADBPath: str, SafelyOrNo: str) -> str:
        ADBP = Path(ADBPath)
        if ADBP.exists():
            pass
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\033[0m")
            sys.exit(1)
        if SafelyOrNo.lower() == "graceful":
            s.run([ADBPath, "shell", "svc", "power", "shutdown"])
        if SafelyOrNo.lower() == "force":
            s.run([ADBPath, "shell", "reboot", "-p"])
        else:
            sys.exit(1)
#-----------------------------------------------------------------
class OpenApp:
    #usage: Open("PathtoADB", "com.dev.package")
    @staticmethod
    def Open(ADBPath: str, PkgName: str) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\033[0m")
        result = s.run(
            [ADBPath, "shell", "am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", PkgName],
            capture_output=True, Text=True
        )
        if result.returncode != 0:
            print(f"\x1b[31mFailed to open: {PkgName}\033[0m")
            sys.exit(1)
    
    @staticmethod
    #usage: Close("PathtoADB", "com.dev.package")
    def Close(ADBPath: str, PkgName: str) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\033[0m")
        result = s.run(
            ["adb", "shell", "am", "force-stop", PkgName],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"\x1b[31mFailed to close: {PkgName}\x1b[0m")
            sys.exit(1)
#--------------------------------------------------------------------------
        



    
