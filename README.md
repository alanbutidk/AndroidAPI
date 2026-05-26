# Android ADB Python Library

A Python library for interacting with Android devices over ADB and Fastboot. Provides helpers for detecting device state, rebooting to specific modes, and opening or closing apps.

---

## Requirements

- Python 3.8+
- ADB and Fastboot installed and accessible on your system
- A connected Android device with USB debugging enabled

---

## Classes

### `DeviceInfo`

A helper class that provides information about the current state of the connected Android device.

#### `DeviceInfo.GetDeviceInfo() -> str`

Detects the current state of the connected device and returns it as a string.

It first attempts to reach the device via ADB. If that fails, it falls back to Fastboot to distinguish between Bootloader and Fastbootd.

Possible return values:

| Return Value | Meaning |
|---|---|
| `"Normal"` | Device is booted into Android (SysUI) |
| `"Recovery"` | Device is in Recovery or ADB Sideload mode |
| `"fastbootd"` | Device is in Fastbootd (userspace fastboot) |
| `"bootloader"` | Device is in the Bootloader |
| `"Unknown"` | Device could not be reached via ADB or Fastboot |

Example:

```python
state = DeviceInfo.GetDeviceInfo()
print(state)
```

---

#### `DeviceInfo._match_states(State: str) -> str | None`

Checks whether the device is already in the state you are trying to reach.

Returns a message string if the device is already on the target state, or `None` if it is not.

This is used internally by `Reboot.RebootTo()` to prevent rebooting into the state the device is already in.

Accepted values for `State` (case insensitive):

| State Argument | Matches Device State |
|---|---|
| `"system"` | `"Normal"` |
| `"recovery"` | `"Recovery"` |
| `"fastbootd"` | `"fastbootd"` |
| `"bootloader"` | `"bootloader"` |

Example:

```python
result = DeviceInfo._match_states("recovery")
if result is not None:
    print(result)
else:
    print("Not in recovery, safe to proceed")
```

---

### `Reboot`

Handles rebooting the connected device to a specific state.

#### `Reboot.RebootTo(ADBPath: str, State: str) -> str`

Reboots the device to the specified state using the ADB binary at the given path.

Before rebooting, it verifies that the ADB path exists and that the device is not already in the target state.

Parameters:

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary, e.g. `"/usr/bin/adb"` |
| `State` | `str` | Target state to reboot into (see table below) |

Accepted values for `State` (case insensitive):

| State Argument | Reboots To |
|---|---|
| `"system"` | Android (SysUI) |
| `"recovery"` | Recovery |
| `"fastbootd"` | Fastbootd |
| `"bootloader"` | Bootloader |

If the ADB path does not exist, the program exits with an error. If the device is already in the target state, the program exits with an error message.

Example:

```python
Reboot.RebootTo("/usr/bin/adb", "recovery")
```

---

### `OpenApp`

Handles launching an app on the connected Android device.

#### `OpenApp.Open(ADBPath: str, PackageName: str) -> str`

Launches the app with the given package name on the device using `am start`.

Parameters:

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary, e.g. `"/usr/bin/adb"` |
| `PackageName` | `str` | Android package name of the app, e.g. `"com.android.chrome"` |

The package name is the app's unique identifier on Android, not its display name. You can find the package name of any installed app by running:

```bash
adb shell pm list packages
```

If the launch fails, the program exits with an error message.

Example:

```python
OpenApp.Open("/usr/bin/adb", "com.android.chrome")
```

---

### `CloseApp`

Handles force stopping an app on the connected Android device.

#### `CloseApp.Close(ADBPath: str, PackageName: str) -> str`

Force stops the app with the given package name using `am force-stop`. This is equivalent to force stopping an app from Android Settings.

Parameters:

| Parameter | Type | Description |
|---|---|---|
| `ADBPath` | `str` | Full path to the ADB binary, e.g. `"/usr/bin/adb"` |
| `PackageName` | `str` | Android package name of the app, e.g. `"com.android.chrome"` |

If the force stop fails, the program exits with an error message.

Example:

```python
CloseApp.Close("/usr/bin/adb", "com.android.chrome")
```

---

## Error Handling

All methods print errors in red using ANSI escape codes and call `sys.exit(1)` on failure. This means any error is fatal and will stop the program. Handle accordingly if you need non-fatal behavior.

---

## Notes

- `DeviceInfo` and `_match_states` are considered helper/internal classes and are not intended to be the primary interface.
- `Reboot`, `OpenApp`, and `CloseApp` are the main classes intended for direct use.
- The device must be connected and recognized by ADB or Fastboot before calling any method.
