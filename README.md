# AndroidAPI

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)
![Python 3.13](https://img.shields.io/badge/Python_3.13-3776AB?logo=python&logoColor=white)
![Python 3.14](https://img.shields.io/badge/Python_3.14-3776AB?logo=python&logoColor=white)
![Python 3.15](https://img.shields.io/badge/Python_3.15-3776AB?logo=python&logoColor=white)

A pure Python library for interacting with Android devices. No ADB binary. No Fastboot binary. No subprocess. Communicates directly with the device over USB or TCP/IP using a custom implementation of the ADB protocol.

---

## Requirements

- Python 3.13+
- `pyusb` for USB connections
- `cryptography` for RSA auth handshake
- A connected Android device with USB debugging enabled

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## File Structure

```
AndroidAPI.py     # device classes: DeviceInfo, DevicePower, OpenApp, AndroidInfo, SideloadAPK
AdbConnect.py     # protocol implementation: AdbUsbConnect, AdbTcpIpConnect, AdbPacket, AdbAuth
requirements.txt  # pyusb, cryptography
```

---

## How It Works

Instead of shelling out to the `adb` binary, this library speaks the ADB protocol directly:

```
Your Code
    |
AndroidAPI.py        (DeviceInfo, DevicePower, OpenApp, AndroidInfo, SideloadAPK)
    |
AdbConnect.py        (AdbTcpIpConnect, AdbUsbConnect)
    |
AdbPacket            (raw 24-byte ADB protocol framing)
    |
AdbAuth              (RSA handshake, key generation)
    |
socket / pyusb       (raw TCP / raw USB)
    |
Device
```

On first connection, an RSA keypair is generated and saved to `adbkey` in the working directory. The device will prompt you to authorize the connection, just like it would with a normal ADB connection.

---

## Connecting to a Device

### USB

```python
from AdbConnect import AdbUsbConnect

conn = AdbUsbConnect()
```

If you have multiple devices connected, pass the serial:

```python
conn = AdbUsbConnect(serial="R5CT21AABCD")
```

### TCP/IP

First enable TCP/IP mode on the device (only needed once):

```bash
adb tcpip 5555
```

Then connect:

```python
from AdbConnect import AdbTcpIpConnect

conn = AdbTcpIpConnect("192.168.1.5")
conn = AdbTcpIpConnect("192.168.1.5", port=5555)
```

### Closing the connection

Always close the connection when done:

```python
conn.close()
```

---

## Classes

### `DeviceInfo`

Helper class for detecting the current state of the connected device.

---

#### `DeviceInfo.GetDeviceInfo(conn) -> str`

Detects the current state of the device by querying system properties over the connection.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |

Possible return values:

| Return Value | Meaning |
|---|---|
| `"Normal"` | Device is booted into Android |
| `"Recovery"` | Device is in Recovery |
| `"fastbootd"` | Device is in Fastbootd |
| `"bootloader"` | Device is in Bootloader |
| `"Unknown"` | State could not be determined |

Example:

```python
state = DeviceInfo.GetDeviceInfo(conn)
print(state)
```

---

#### `DeviceInfo._match_states(conn, State) -> str | None`

Checks whether the device is already in the target state. Returns a message string if it is, or `None` if it is not. Used internally by `DevicePower.RebootTo()`.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |
| `State` | `str` | Target state to check against (case insensitive) |

Accepted values for `State`:

| Value | Matches Device State |
|---|---|
| `"system"` | `"Normal"` |
| `"recovery"` | `"Recovery"` |
| `"fastbootd"` | `"fastbootd"` |
| `"bootloader"` | `"bootloader"` |

Example:

```python
match = DeviceInfo._match_states(conn, "recovery")
if match is not None:
    print(match)
else:
    print("Not in recovery, safe to proceed")
```

---

### `DevicePower`

Handles rebooting and shutting down the device.

---

#### `DevicePower.RebootTo(conn, State) -> None`

Reboots the device to the specified state. Exits with an error if the device is already in the target state.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |
| `State` | `str` | Target state to reboot into (case insensitive) |

Accepted values for `State`:

| Value | Reboots To |
|---|---|
| `"system"` | Android |
| `"recovery"` | Recovery |
| `"fastbootd"` | Fastbootd |
| `"bootloader"` | Bootloader |

Example:

```python
DevicePower.RebootTo(conn, "recovery")
```

---

#### `DevicePower.Shutdown(conn, SafelyOrNo) -> None`

Shuts down the device either gracefully or forcefully.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |
| `SafelyOrNo` | `str` | Shutdown mode: `"graceful"` or `"force"` |

| Value | Behaviour |
|---|---|
| `"graceful"` | Clean shutdown via `svc power shutdown` |
| `"force"` | Hard shutdown via `reboot -p` |

Example:

```python
DevicePower.Shutdown(conn, "graceful")
```

---

### `OpenApp`

Handles launching and force stopping apps on the device.

---

#### `OpenApp.Open(conn, PkgName) -> None`

Launches an app by its package name using `am start`.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |
| `PkgName` | `str` | Android package name, e.g. `"com.android.chrome"` |

Example:

```python
OpenApp.Open(conn, "com.android.chrome")
```

---

#### `OpenApp.Close(conn, PkgName) -> None`

Force stops an app by its package name using `am force-stop`.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |
| `PkgName` | `str` | Android package name, e.g. `"com.android.chrome"` |

Example:

```python
OpenApp.Close(conn, "com.android.chrome")
```

---

### `AndroidInfo`

Queries device information via `getprop`. All methods share a `say` parameter: if `True`, the value is printed. If `False` (default), it is returned as a string.

---

#### `AndroidInfo.AndroidVersion(conn, say=False) -> str | None`

Returns the Android version, e.g. `"14"`.

```python
AndroidInfo.AndroidVersion(conn, say=True)
version = AndroidInfo.AndroidVersion(conn)
```

---

#### `AndroidInfo.AndroidSDKVersion(conn, say=False) -> str | None`

Returns the SDK level, e.g. `"34"`.

```python
AndroidInfo.AndroidSDKVersion(conn, say=True)
sdk = AndroidInfo.AndroidSDKVersion(conn)
```

---

#### `AndroidInfo.AndroidBuildID(conn, say=False) -> str | None`

Returns the build ID, e.g. `"UQ1A.240205.002"`.

```python
AndroidInfo.AndroidBuildID(conn, say=True)
build = AndroidInfo.AndroidBuildID(conn)
```

---

### `SideloadAPK`

Handles installing APK files onto the device.

---

#### `SideloadAPK.SideloadAPK(conn, APKPath) -> None`

Installs an APK onto the device using `pm install`. Validates that the path exists and that the file has a `.apk` extension before attempting installation.

| Parameter | Type | Description |
|---|---|---|
| `conn` | `AdbConnection` | Active USB or TCP/IP connection |
| `APKPath` | `str` | Full path to the APK file on the host machine |

Example:

```python
SideloadAPK.SideloadAPK(conn, "/home/user/Downloads/myapp.apk")
```

---

## Full Example

```python
from AdbConnect import AdbUsbConnect
from AndroidAPI import DeviceInfo, DevicePower, OpenApp, AndroidInfo, SideloadAPK

conn = AdbUsbConnect()

print(DeviceInfo.GetDeviceInfo(conn))

AndroidInfo.AndroidVersion(conn, say=True)
AndroidInfo.AndroidSDKVersion(conn, say=True)
AndroidInfo.AndroidBuildID(conn, say=True)

OpenApp.Open(conn, "com.android.chrome")
OpenApp.Close(conn, "com.android.chrome")

SideloadAPK.SideloadAPK(conn, "/home/user/Downloads/myapp.apk")

DevicePower.Shutdown(conn, "graceful")

conn.close()
```

---

## Error Handling

All methods print errors in red using ANSI escape codes and call their own ```custom exceptions```, For more info: See the code!

---

## Notes

- No `adb` or `fastboot` binary required on the host machine
- No `subprocess` calls anywhere in the codebase
- The RSA keypair is auto-generated on first run and saved to `adbkey` in the working directory
- `DeviceInfo` is a helper class and is not intended to be the primary interface
- Always call `conn.close()` when finished to release the USB or socket resource