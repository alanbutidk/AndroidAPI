# AndroidAPI

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Python 3.13](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=white)
![Python 3.14](https://img.shields.io/badge/Python_3.14-3776AB?logo=python&logoColor=white)
![Python 3.15](https://img.shields.io/badge/Python_3.15-3776AB?logo=python&logoColor=white)

A Python library for interacting with Android devices over ADB and Fastboot. Provides helpers for detecting device state, rebooting to specific modes, opening and closing apps, querying device info, and sideloading APKs. All APIs support multi-device targeting via an optional `DeviceSerial` parameter.

---

## Requirements

- Python 3.13+
- ADB and Fastboot installed on your system
- A connected Android device with USB debugging enabled

---

## Installation

Copy `AndroidAPI.py` into your project directory and import from it directly:

```python
from AndroidAPI import DeviceInfo, DevicePower, OpenApp, AndroidInfo, SideloadAPK
```

---

## Multi-Device Support

Every method accepts an optional `DeviceSerial` parameter. If you have multiple devices connected, pass the serial to target a specific one. If you only have one device connected, you can omit it entirely and it will default to `None`, meaning ADB will target the only connected device automatically.

You can find the serial of your connected devices by running:

```bash
adb devices
```

Example with serial:

```python
AndroidInfo.AndroidVersion("/usr/bin/adb", say=True, DeviceSerial="R5CT21AABCD")
```

Example without serial (single device):

```python
AndroidInfo.AndroidVersion("/usr/bin/adb", say=True)
```

---

## Classes

### `DeviceInfo`

Helper class for detecting the current state of the connected device.

---

#### `DeviceInfo.GetDeviceInfo(ADBPath, FastbootPath, DeviceSerial=None) -> str`

Detects the current state of the device. Tries ADB first, then falls back to Fastboot.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `FastbootPath` | `str` | Full path to the Fastboot binary |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

Possible return values:

| Return Value | Meaning |
|---|---|
| `"Normal"` | Device is booted into Android |
| `"Recovery"` | Device is in Recovery or Sideload mode |
| `"fastbootd"` | Device is in Fastbootd |
| `"bootloader"` | Device is in Bootloader |
| `"Unknown"` | Device could not be reached |

Example:

```python
state = DeviceInfo.GetDeviceInfo("/usr/bin/adb", "/usr/bin/fastboot")
print(state)
```

---

#### `DeviceInfo._match_states(ADBPath, FastbootPath, State, DeviceSerial=None) -> str | None`

Checks whether the device is already in the target state. Returns a message string if it is, or `None` if it is not. Used internally by `DevicePower.RebootTo()`.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `FastbootPath` | `str` | Full path to the Fastboot binary |
| `State` | `str` | Target state to check against (case insensitive) |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

Accepted values for `State`:

| Value | Matches Device State |
|---|---|
| `"system"` | `"Normal"` |
| `"recovery"` | `"Recovery"` |
| `"fastbootd"` | `"fastbootd"` |
| `"bootloader"` | `"bootloader"` |

Example:

```python
match = DeviceInfo._match_states("/usr/bin/adb", "/usr/bin/fastboot", "recovery")
if match is not None:
    print(match)
else:
    print("Not in recovery, safe to proceed")
```

---

### `DevicePower`

Handles rebooting and shutting down the device.

---

#### `DevicePower.RebootTo(ADBPath, FastbootPath, State, DeviceSerial=None) -> str`

Reboots the device to the specified state. Exits with an error if the device is already in the target state.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `FastbootPath` | `str` | Full path to the Fastboot binary |
| `State` | `str` | Target state to reboot into (case insensitive) |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

Accepted values for `State`:

| Value | Reboots To |
|---|---|
| `"system"` | Android |
| `"recovery"` | Recovery |
| `"fastbootd"` | Fastbootd |
| `"bootloader"` | Bootloader |

Example:

```python
DevicePower.RebootTo("/usr/bin/adb", "/usr/bin/fastboot", "recovery")
```

---

#### `DevicePower.Shutdown(ADBPath, SafelyOrNo, DeviceSerial=None) -> str`

Shuts down the device either gracefully or forcefully.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `SafelyOrNo` | `str` | Shutdown mode: `"graceful"` or `"force"` |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

| Value | Behaviour |
|---|---|
| `"graceful"` | Clean shutdown via `svc power shutdown` |
| `"force"` | Hard shutdown via `reboot -p` |

Example:

```python
DevicePower.Shutdown("/usr/bin/adb", "graceful")
```

---

### `OpenApp`

Handles launching and force stopping apps on the device.

---

#### `OpenApp.Open(ADBPath, PkgName, DeviceSerial=None) -> str`

Launches an app by its package name using `am start`.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `PkgName` | `str` | Android package name, e.g. `"com.android.chrome"` |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

To find the package name of an installed app:

```bash
adb shell pm list packages
```

Example:

```python
OpenApp.Open("/usr/bin/adb", "com.android.chrome")
```

---

#### `OpenApp.Close(ADBPath, PkgName, DeviceSerial=None) -> str`

Force stops an app by its package name using `am force-stop`. Equivalent to force stopping from Android Settings.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `PkgName` | `str` | Android package name, e.g. `"com.android.chrome"` |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

Example:

```python
OpenApp.Close("/usr/bin/adb", "com.android.chrome")
```

---

### `AndroidInfo`

Queries device information via `getprop`.

All methods share the same `say` parameter: if `True`, the value is printed to the console. If `False` (default), it is returned as a string.

---

#### `AndroidInfo.AndroidVersion(ADBPath, say=False, DeviceSerial=None) -> str`

Returns the Android version, e.g. `"14"`.

Example:

```python
AndroidInfo.AndroidVersion("/usr/bin/adb", say=True)
version = AndroidInfo.AndroidVersion("/usr/bin/adb")
```

---

#### `AndroidInfo.AndroidSDKVersion(ADBPath, say=False, DeviceSerial=None) -> str`

Returns the SDK level, e.g. `"34"`.

Example:

```python
AndroidInfo.AndroidSDKVersion("/usr/bin/adb", say=True)
sdk = AndroidInfo.AndroidSDKVersion("/usr/bin/adb")
```

---

#### `AndroidInfo.AndroidBuildID(ADBPath, say=False, DeviceSerial=None) -> str`

Returns the build ID, e.g. `"UQ1A.240205.002"`.

Example:

```python
AndroidInfo.AndroidBuildID("/usr/bin/adb", say=True)
build = AndroidInfo.AndroidBuildID("/usr/bin/adb")
```

---

### `SideloadAPK`

Handles installing APK files onto the device.

---

#### `SideloadAPK.SideloadAPK(ADBPath, APKPath, DeviceSerial=None) -> str`

Installs an APK onto the device using `adb install -r`. Validates that both paths exist and that the file has a `.apk` extension before attempting installation.

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary |
| `APKPath` | `str` | Full path to the APK file |
| `DeviceSerial` | `str` | Optional device serial for multi-device setups |

Example:

```python
SideloadAPK.SideloadAPK("/usr/bin/adb", "/home/user/Downloads/myapp.apk")
```

---

## Error Handling

All methods print errors in red using ANSI escape codes and call `sys.exit(1)` on failure, making every error fatal. If you need non-fatal behavior, wrap calls in a `try/except SystemExit`.

---

## Notes

- `DeviceInfo` is a helper class and is not intended to be the primary interface.
- `DevicePower`, `OpenApp`, `AndroidInfo`, and `SideloadAPK` are the main classes for direct use.
- The device must be reachable via ADB or Fastboot before calling any method.
- `DeviceSerial` is always the last parameter on every method and always defaults to `None`.