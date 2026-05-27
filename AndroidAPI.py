import subprocess as s
import sys
from pathlib import Path
class VersionError(Exception):
    pass
class SideloadError(Exception):
    pass
s.run("", shell=True)
#Not considered a main class, RATHER helper classes!
class DeviceInfo:
    @staticmethod
    #Give device info -> return, usage: a = GetDeviceInfo()
    def GetDeviceInfo(ADBPath: str, FastbootPath: str, DeviceSerial: str = None):
        ADBP, FastP = Path(ADBPath), Path(FastbootPath)
        if not ADBP.exists() and not FastP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path for ADB!\x1b[0m")
            raise FileNotFoundError
        adb_cmd = [ADBPath]
        if DeviceSerial:
            adb_cmd += ["-s", DeviceSerial]
        adb_cmd += ["get-state"]
        try:
            adb = s.run(adb_cmd, capture_output=True, text=True)
        except OSError as e:
            print(f"\x1b[31mOS error while running ADB: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while running ADB: {e}\x1b[0m")
            raise
        except KeyboardInterrupt:
            print(f"\x1b[31mStopped Operation!\x1b[0m")
        if adb.returncode == 0:
            state = adb.stdout.strip()
            if state == "device":
                return "Normal"
            elif state == "recovery" or state == "sideload":
                return "Recovery"
        fastboot_cmd = [FastbootPath]
        if DeviceSerial:
            fastboot_cmd += ["-s", DeviceSerial]
        fastboot_cmd += ["getvar", "current-slot"]
        try:
            fastboot = s.run(fastboot_cmd, capture_output=True, text=True)
        except OSError as e:
            print(f"\x1b[31mOS error while running Fastboot: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while running Fastboot: {e}\x1b[0m")
            raise
        if fastboot.returncode == 0:
            combined = (fastboot.stdout + fastboot.stderr).lower()
            if "fastbootd" in combined:
                return "fastbootd"
            return "bootloader"
        return "Unknown"

    @staticmethod
    #match device state with argument state, usage: a = _match_states("MyState!")
    def _match_states(ADBPath: str, FastbootPath: str, State: str, DeviceSerial: str = None) -> str:
        match_func = DeviceInfo.GetDeviceInfo(ADBPath, FastbootPath, DeviceSerial)
        if match_func == "Normal" and State.lower() == "system":
            return f"Trying to get to {State} but on {match_func}!"
        elif match_func == "fastbootd" and State.lower() == "fastbootd":
            return f"Trying to get to {State} but on {match_func}!"
        elif match_func == "Recovery" and State.lower() == "recovery":
            return f"Trying to get to {State} but on {match_func}!"
        elif match_func == "bootloader" and State.lower() == "bootloader":
            return f"Trying to get to {State} but on {match_func}!"
        return None

#Main classes--------------------------------------------------------
class DevicePower:
    #RebootTo -> ADBPath, 'reboot', State
    @staticmethod
    def RebootTo(ADBPath: str, FastbootPath: str, State: str, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\x1b[0m")
            raise FileNotFoundError
        b = DeviceInfo._match_states(ADBPath, FastbootPath, State, DeviceSerial)
        if b is not None:
            print(f"\x1b[31m{b}\x1b[0m")
            raise RuntimeError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            if State.lower() == "system":
                s.run(cmd + ["reboot"])
            elif State.lower() == "recovery":
                s.run(cmd + ["reboot", "recovery"])
            elif State.lower() == "fastbootd":
                s.run(cmd + ["reboot", "fastboot"])
            elif State.lower() == "bootloader":
                s.run(cmd + ["reboot", "bootloader"])
            else:
                print(f"\x1b[31mUnknown state: {State}\x1b[0m")
                raise ValueError
        except OSError as e:
            print(f"\x1b[31mOS error while rebooting: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while rebooting: {e}\x1b[0m")
            raise

    #Shutdown, ADBPath, graceful/force -> adb shell 'cmd'
    @staticmethod
    def Shutdown(ADBPath: str, SafelyOrNo: str, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\x1b[0m")
            raise FileNotFoundError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            if SafelyOrNo.lower() == "graceful":
                s.run(cmd + ["shell", "svc", "power", "shutdown"])
            elif SafelyOrNo.lower() == "force":
                s.run(cmd + ["shell", "reboot", "-p"])
            else:
                print(f"\x1b[31mUnknown shutdown mode: {SafelyOrNo}\x1b[0m")
                raise ValueError
        except OSError as e:
            print(f"\x1b[31mOS error while shutting down: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while shutting down: {e}\x1b[0m")
            raise

#-----------------------------------------------------------------
class OpenApp:
    #usage: Open("PathtoADB", "com.dev.package")
    @staticmethod
    def Open(ADBPath: str, PkgName: str, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\x1b[0m")
            raise FileNotFoundError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            result = s.run(
                cmd + ["shell", "am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", "-p", PkgName],
                capture_output=True, text=True
            )
        except OSError as e:
            print(f"\x1b[31mOS error while opening app: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while opening app: {e}\x1b[0m")
            raise
        if result.returncode != 0:
            print(f"\x1b[31mFailed to open: {PkgName}\x1b[0m")
            raise RuntimeError

    @staticmethod
    #usage: Close("PathtoADB", "com.dev.company.package")
    def Close(ADBPath: str, PkgName: str, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path to ADB!\x1b[0m")
            raise FileNotFoundError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            result = s.run(
                cmd + ["shell", "am", "force-stop", PkgName],
                capture_output=True, text=True
            )
        except OSError as e:
            print(f"\x1b[31mOS error while closing app: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while closing app: {e}\x1b[0m")
            raise
        if result.returncode != 0:
            print(f"\x1b[31mFailed to close: {PkgName}\x1b[0m")
            raise RuntimeError

#----------------------------------------------------------------
class AndroidInfo:
    @staticmethod
    def AndroidVersion(ADBPath: str, say=False, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path for ADB!\x1b[0m")
            raise FileNotFoundError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            version = s.run(cmd + ["shell", "getprop", "ro.build.version.release"], capture_output=True, text=True)
        except OSError as e:
            print(f"\x1b[31mOS error while getting Android version: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while getting Android version: {e}\x1b[0m")
            raise
        if version.returncode != 0:
            print("\x1b[31mFailed to get version!\x1b[0m")
            raise VersionError
        if say:
            print(version.stdout.strip())
        else:
            return version.stdout.strip()

    @staticmethod
    def AndroidSDKVersion(ADBPath: str, say=False, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path for ADB!\x1b[0m")
            raise FileNotFoundError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            version = s.run(cmd + ["shell", "getprop", "ro.build.version.sdk"], capture_output=True, text=True)
        except OSError as e:
            print(f"\x1b[31mOS error while getting SDK version: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while getting SDK version: {e}\x1b[0m")
            raise
        if version.returncode != 0:
            print(f"\x1b[31mFailed to get version!\x1b[0m")
            raise VersionError
        if say:
            print(version.stdout.strip())
        else:
            return version.stdout.strip()

    #Usage: AndroidBuildID("PathtoADB", say=True)
    @staticmethod
    def AndroidBuildID(ADBPath: str, say=False, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path for ADB!\x1b[0m")
            raise FileNotFoundError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            version = s.run(cmd + ["shell", "getprop", "ro.build.id"], capture_output=True, text=True)
        except OSError as e:
            print(f"\x1b[31mOS error while getting build ID: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while getting build ID: {e}\x1b[0m")
            raise
        if version.returncode != 0:
            print("\x1b[31mFailed to get version!\x1b[0m")
            raise VersionError
        if say:
            print(version.stdout.strip())
        else:
            return version.stdout.strip()

#--------------------------------------------------------------------------
class SideloadAPK:
    @staticmethod
    def SideloadAPK(ADBPath: str, APKPath: str, DeviceSerial: str = None) -> str:
        ADBP = Path(ADBPath)
        APKP = Path(APKPath)
        if not ADBP.exists():
            print(f"\x1b[31mPath: {ADBPath} is not a correct path for ADB!\x1b[0m")
            raise SideloadError
        if not APKP.exists():
            print(f"\x1b[31mPath: {APKPath} is not a correct path for the APK!\x1b[0m")
            raise SideloadError
        if not APKP.suffix.lower() == ".apk":
            print(f"\x1b[31mAPK: {APKPath} is not a .apk file!\x1b[0m")
            raise SideloadError
        cmd = [ADBPath]
        if DeviceSerial:
            cmd += ["-s", DeviceSerial]
        try:
            result = s.run(cmd + ["install", "-r", APKPath], capture_output=True, text=True)
        except OSError as e:
            print(f"\x1b[31mOS error while sideloading APK: {e}\x1b[0m")
            raise
        except ValueError as e:
            print(f"\x1b[33mValue error while sideloading APK: {e}\x1b[0m")
            raise
        if result.returncode != 0:
            print("\x1b[31mFailed to sideload app!\x1b[0m")
            raise SideloadError

#------------------------------------------------------------------------
