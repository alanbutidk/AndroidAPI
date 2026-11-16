import sys
from pathlib import Path
from AdbConnect import AdbConnection

"""Copyright (c) 2026 Alan. All Rights Reserved."""

# Custom exceptions. If you write code on top of this and want to catch them,
# don't touch the excepthook below, just catch them normally.
#
# RebootToOnState     -> tried to reboot into the state the device is already in
# UnknownState        -> that state doesn't exist
# UnknownShutdownMode -> mode wasn't "graceful" or "force"
# ErrorWhileHandleApp -> couldn't open/close the app
# FailedToGetDeviceInfo -> couldn't read info from the device
# WrongFilePassedError  -> file isn't an .apk
# FailedToSideloadApp   -> pm install failed


class RebootToOnState(Exception):
    pass


class UnknownState(Exception):
    pass


class UnknownShutdownMode(Exception):
    pass


class ErrorWhileHandleApp(Exception):
    pass


class FailedToGetDeviceInfo(Exception):
    pass


class WrongFilePassedError(Exception):
    pass


class FailedToSideloadApp(Exception):
    pass


CUSTOM_ERRORS = (
    RebootToOnState,
    UnknownState,
    UnknownShutdownMode,
    ErrorWhileHandleApp,
    FailedToGetDeviceInfo,
    WrongFilePassedError,
    FailedToSideloadApp,
)


# Our own errors print as a single clean line, everything else gets the normal traceback
def Customclass_Handler(exctype, value, traceback):
    if issubclass(exctype, CUSTOM_ERRORS):
        print(f"{exctype.__name__}: {value}")
    else:
        sys.__excepthook__(exctype, value, traceback)


sys.excepthook = Customclass_Handler


# Helper classes, not meant to be used much on their own
class DeviceInfo:
    def __init__(self, conn: AdbConnection):
        self.conn = conn

    # Returns the current boot state: Normal, Recovery, fastbootd, bootloader or Unknown
    def GetDeviceInfo(self) -> str:
        result: str = self.conn.shell("getprop sys.boot_completed").strip()
        if result == "1":
            return "Normal"
        bootmode: str = self.conn.shell("getprop ro.bootmode").strip()
        if bootmode == "recovery":
            return "Recovery"
        if bootmode == "fastbootd":
            return "fastbootd"
        if bootmode == "bootloader":
            return "bootloader"
        return "Unknown"

    # Checks if the state we want is the one we're already in.
    # Gives back an error message if so, None if we're good to go.
    def _match_states(self, State: str) -> str | None:
        current: str = self.GetDeviceInfo()
        wanted: str = State.lower()
        if current == "Normal" and wanted == "system":
            return f"Trying to get to {State} but on {current}!"
        if current == "fastbootd" and wanted == "fastbootd":
            return f"Trying to get to {State} but on {current}!"
        if current == "Recovery" and wanted == "recovery":
            return f"Trying to get to {State} but on {current}!"
        if current == "bootloader" and wanted == "bootloader":
            return f"Trying to get to {State} but on {current}!"
        return None


# Main classes ---------------------------------------------------------
class DevicePower:
    def __init__(self, conn: AdbConnection):
        self.conn = conn
        self.info = DeviceInfo(conn)

    # usage: DevicePower(conn).RebootTo("recovery")
    def RebootTo(self, State: str) -> None:
        err: str | None = self.info._match_states(State)
        if err is not None:
            raise RebootToOnState(f"\x1b[31m{err}\x1b[0m")
        if State.lower() == "system":
            self.conn.shell("reboot")
        elif State.lower() == "recovery":
            self.conn.shell("reboot recovery")
        elif State.lower() == "fastbootd":
            self.conn.shell("reboot fastboot")
        elif State.lower() == "bootloader":
            self.conn.shell("reboot bootloader")
        else:
            raise UnknownState(f"\x1b[31mUnknown state: {State}\x1b[0m")

    # usage: DevicePower(conn).Shutdown("graceful") or "force"
    def Shutdown(self, SafelyOrNo: str) -> None:
        if SafelyOrNo.lower() == "graceful":
            self.conn.shell("svc power shutdown")
        elif SafelyOrNo.lower() == "force":
            self.conn.shell("reboot -p")
        else:
            raise UnknownShutdownMode(
                f"\x1b[31mUnknown shutdown mode: {SafelyOrNo}\x1b[0m"
            )


# ----------------------------------------------------------------------
class OpenApp:
    def __init__(self, conn: AdbConnection):
        self.conn = conn

    # usage: OpenApp(conn).Open("com.dev.package")
    def Open(self, PkgName: str) -> None:
        result: str = self.conn.shell(
            f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -p {PkgName}"
        )
        if "Error" in result or "Exception" in result:
            raise ErrorWhileHandleApp(f"\x1b[31mFailed to open: {PkgName}\x1b[0m")

    # usage: OpenApp(conn).Close("com.dev.package")
    def Close(self, PkgName: str) -> None:
        result: str = self.conn.shell(f"am force-stop {PkgName}")
        if "Error" in result or "Exception" in result:
            raise ErrorWhileHandleApp(f"\x1b[31mFailed to close: {PkgName}\x1b[0m")


# ----------------------------------------------------------------------
# Each getter returns the value, or prints it if say=True
class AndroidInfo:
    def __init__(self, conn: AdbConnection):
        self.conn = conn

    def _getprop(self, prop: str, label: str) -> str:
        value: str = self.conn.shell(f"getprop {prop}").strip()
        if not value:
            raise FailedToGetDeviceInfo(f"\x1b[31mFailed to get {label}!\x1b[0m")
        return value

    def AndroidVersion(self, say: bool = False) -> str | None:
        version: str = self._getprop("ro.build.version.release", "version")
        if say:
            print(version)
        else:
            return version

    def AndroidSDKVersion(self, say: bool = False) -> str | None:
        version: str = self._getprop("ro.build.version.sdk", "SDK version")
        if say:
            print(version)
        else:
            return version

    # usage: AndroidInfo(conn).AndroidBuildID(say=True)
    def AndroidBuildID(self, say: bool = False) -> str | None:
        version: str = self._getprop("ro.build.id", "build ID")
        if say:
            print(version)
        else:
            return version


# ----------------------------------------------------------------------
class SideloadAPK:
    def __init__(self, conn: AdbConnection):
        self.conn = conn

    # usage: SideloadAPK(conn).SideloadAPK("path/to/app.apk")
    def SideloadAPK(self, APKPath: str) -> None:
        APKP: Path = Path(APKPath)
        if not APKP.exists():
            raise FileNotFoundError(
                f"\x1b[31mPath: {APKPath} is not a correct path for the APK!\x1b[0m"
            )
        if APKP.suffix.lower() != ".apk":
            raise WrongFilePassedError(
                f"\x1b[31mAPK: {APKPath} is not a .apk file!\x1b[0m"
            )
        result: str = self.conn.shell(f"pm install -r {APKPath}")
        if "Failure" in result or "Error" in result:
            raise FailedToSideloadApp("\x1b[31mFailed to sideload app!\x1b[0m")