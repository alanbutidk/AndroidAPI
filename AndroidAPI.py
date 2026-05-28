# All imports used in the code
import os;os.system("") #to enable VT on windows (Basically color support)
import sys
from pathlib import Path
from AdbConnect import AdbConnection
#--------------------------------------------------------------------------------
"""Copyright (c) 2026 Alan. All Rights Reserved."""
#--------------------------------------------------------------------------------
"""These are the custom classes we are using in the code!
If you are making code and want to use the exceptions, dont modify the master function...
-------------------------------------------------------------------------------------------------------
RebootToOnState -> Error for rebooting to state you are on.
UnknownState -> Given state that doesnt exist
UnknownShutdownMode -> Not a option between ```graceful and force```
ErrorWhileHandleApp -> couldnt close/open a app
FailedToGetDeviceInfo -> was not able to retrieve info about device
WrongFilePassedError -> not a .apk or any other file
FailedToSideloadApp -> was not able to sideload app into device"""


class RebootToOnState(Exception): pass
class UnknownState(Exception): pass
class UnknownShutdownMode(Exception): pass
class ErrorWhileHandleApp(Exception): pass
class FailedToGetDeviceInfo(Exception): pass
class WrongFilePassedError(Exception): pass
class FailedToSideloadApp(Exception): pass


#Master function to handle all of the custom classes
def Customclass_Handler(exctype, value, traceback):
    #check for the classes here
    if issubclass(exctype, RebootToOnState):
        print(f"{exctype.__name__}: {value}")
        
    elif issubclass(exctype, UnknownState):
        print(f"{exctype.__name__}: {value}")
        
    elif issubclass(exctype, UnknownShutdownMode):
        print(f"{exctype.__name__}: {value}")
        
    elif issubclass(exctype, ErrorWhileHandleApp):
        print(f"{exctype.__name__}: {value}")
        
    elif issubclass(exctype, FailedToGetDeviceInfo):
        print(f"{exctype.__name__}: {value}")
        
    elif issubclass(exctype, WrongFilePassedError):
        print(f"{exctype.__name__}: {value}")
        
    elif issubclass(exctype, FailedToSideloadApp):
        print(f"{exctype.__name__}: {value}")
        
    else:
        # Fallback for standard Python errors (Like FileNotFoundError)
        sys.__excepthook__(exctype, value, traceback)


# Now register the function to work fine!
sys.excepthook = Customclass_Handler


#Not considered a main class, RATHER helper classes!
class DeviceInfo:
    @staticmethod
    #Give device info -> return, usage: a = GetDeviceInfo(conn)
    def GetDeviceInfo(conn: AdbConnection) -> str:
        result: str = conn.shell("getprop sys.boot_completed").strip()
        if result == "1":
            return "Normal"
        recovery: str = conn.shell("getprop ro.bootmode").strip()
        if recovery == "recovery":
            return "Recovery"
        fastbootd: str = conn.shell("getprop ro.bootmode").strip()
        if fastbootd == "fastbootd":
            return "fastbootd"
        if fastbootd == "bootloader":
            return "bootloader"
        return "Unknown"

    @staticmethod
    #match device state with argument state, usage: a = _match_states(conn, "MyState!")
    def _match_states(conn: AdbConnection, State: str) -> str | None:
        match_func: str = DeviceInfo.GetDeviceInfo(conn)
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
    #RebootTo -> conn, State
    @staticmethod
    def RebootTo(conn: AdbConnection, State: str) -> None:
        b: str | None = DeviceInfo._match_states(conn, State)
        if b is not None:
            raise RebootToOnState(f"\x1b[31m{b}\x1b[0m")
        if State.lower() == "system":
            conn.shell("reboot")
        elif State.lower() == "recovery":
            conn.shell("reboot recovery")
        elif State.lower() == "fastbootd":
            conn.shell("reboot fastboot")
        elif State.lower() == "bootloader":
            conn.shell("reboot bootloader")
        else:
            raise UnknownState(f"\x1b[31mUnknown state: {State}\x1b[0m")

    #Shutdown, conn, graceful/force -> shell cmd
    @staticmethod
    def Shutdown(conn: AdbConnection, SafelyOrNo: str) -> None:
        if SafelyOrNo.lower() == "graceful":
            conn.shell("svc power shutdown")
        elif SafelyOrNo.lower() == "force":
            conn.shell("reboot -p")
        else:
            raise UnknownShutdownMode(f"\x1b[31mUnknown shutdown mode: {SafelyOrNo}\x1b[0m")

#-----------------------------------------------------------------
class OpenApp:
    #usage: Open(conn, "com.dev.package")
    @staticmethod
    def Open(conn: AdbConnection, PkgName: str) -> None:
        result: str = conn.shell(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {PkgName}")
        if "Error" in result or "Exception" in result:
            raise ErrorWhileHandleApp(f"\x1b[31mFailed to open: {PkgName}\x1b[0m")

    #usage: Close(conn, "com.dev.company.package")
    @staticmethod
    def Close(conn: AdbConnection, PkgName: str) -> None:
        result: str = conn.shell(f"am force-stop {PkgName}")
        if "Error" in result or "Exception" in result:
            raise ErrorWhileHandleApp(f"\x1b[31mFailed to close: {PkgName}\x1b[0m")

#----------------------------------------------------------------
class AndroidInfo:
    @staticmethod
    def AndroidVersion(conn: AdbConnection, say: bool = False) -> str | None:
        version: str = conn.shell("getprop ro.build.version.release").strip()
        if not version:
            raise FailedToGetDeviceInfo("\x1b[31mFailed to get version!\x1b[0m")
        if say:
            print(version)
        else:
            return version

    @staticmethod
    def AndroidSDKVersion(conn: AdbConnection, say: bool = False) -> str | None:
        version: str = conn.shell("getprop ro.build.version.sdk").strip()
        if not version:
            raise FailedToGetDeviceInfo(f"\x1b[31mFailed to get SDK version!\x1b[0m")
        if say:
            print(version)
        else:
            return version

    #Usage: AndroidBuildID(conn, say=True)
    @staticmethod
    def AndroidBuildID(conn: AdbConnection, say: bool = False) -> str | None:
        version: str = conn.shell("getprop ro.build.id").strip()
        if not version:
            raise FailedToGetDeviceInfo("\x1b[31mFailed to get build ID!\x1b[0m")
        if say:
            print(version)
        else:
            return version

#--------------------------------------------------------------------------
class SideloadAPK:
    @staticmethod
    def SideloadAPK(conn: AdbConnection, APKPath: str) -> None:
        APKP: Path = Path(APKPath)
        if not APKP.exists():
            raise FileNotFoundError(f"\x1b[31mPath: {APKPath} is not a correct path for the APK!\x1b[0m")
        if not APKP.suffix.lower() == ".apk":
            raise WrongFilePassedError(f"\x1b[31mAPK: {APKPath} is not a .apk file!\x1b[0m")
        result: str = conn.shell(f"pm install -r {APKPath}")
        if "Failure" in result or "Error" in result:
            raise FailedToSideloadApp("\x1b[31mFailed to sideload app!\x1b[0m")
#------------------------------------------------------------------------

