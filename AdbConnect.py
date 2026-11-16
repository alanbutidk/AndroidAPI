import base64
import ctypes as c
import os
import platform
import socket
import struct
import sys
from abc import ABC, abstractmethod
from pathlib import Path

import usb.backend.libusb1
import usb.core
import usb.util
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, utils

# turn on ANSI colors in the windows console
if sys.platform == "win32":
    k32 = c.windll.kernel32
    hStdout = k32.GetStdHandle(-11)
    mode = c.c_ulong()
    k32.GetConsoleMode(hStdout, c.byref(mode))
    k32.SetConsoleMode(hStdout, mode.value | 0x0004)


class DLLHandle:
    def DLLWrap(self):
        # outside windows libusb comes from the system, no dll needed
        if sys.platform != "win32":
            return usb.backend.libusb1.get_backend()
        DllPath = Path("libusb-1.0.dll").resolve()
        if not DllPath.exists():
            raise usb.core.NoBackendError(
                "\x1b[31mCould not resolve dll: 'libusb-1.0.dll' for USB Backend!\033[0m"
            )
        os.add_dll_directory(str(DllPath.parent))
        return usb.backend.libusb1.get_backend(find_library=lambda x: str(DllPath))


CMD_CNXN: int = 0x4E584E43
CMD_AUTH: int = 0x48545541
CMD_OPEN: int = 0x4E45504F
CMD_OKAY: int = 0x59414B4F
CMD_WRTE: int = 0x45545257
CMD_CLSE: int = 0x45534C43

AUTH_TOKEN: int = 1
AUTH_SIGNATURE: int = 2
AUTH_RSAPUBKEY: int = 3

# same values as adb.h
A_VERSION_MIN: int = 0x01000000
A_VERSION_SKIP_CHECKSUM: int = 0x01000001
A_VERSION: int = A_VERSION_SKIP_CHECKSUM
MAX_PAYLOAD: int = 1024 * 1024

# adb tags its interface with these, the interface number itself can be anything
ADB_CLASS: int = 0xFF
ADB_SUBCLASS: int = 0x42
ADB_PROTOCOL: int = 0x01

TIMEOUT_MS: int = 5000
# waiting for someone to tap "allow" on the phone takes a while
AUTH_TIMEOUT_MS: int = 60000


class AdbPacket:
    def __init__(self, command: int, arg0: int, arg1: int, data: bytes = b""):
        self.command: int = command
        self.arg0: int = arg0
        self.arg1: int = arg1
        self.data: bytes = data if isinstance(data, bytes) else data.encode()
        self.data_len: int = len(self.data)
        self.data_crc: int = sum(self.data) & 0xFFFFFFFF

    def header(self, skip_checksum: bool = False) -> bytes:
        magic: int = (self.command ^ 0xFFFFFFFF) & 0xFFFFFFFF
        check: int = 0 if skip_checksum else self.data_crc
        return struct.pack(
            "<6I", self.command, self.arg0, self.arg1, self.data_len, check, magic
        )

    def encode(self, skip_checksum: bool = False) -> bytes:
        return self.header(skip_checksum) + self.data


def _encode_adb_rsa_pubkey(public_key: rsa.RSAPublicKey) -> bytes:
    numbers = public_key.public_numbers()
    n = numbers.n
    e = numbers.e

    RSANUMWORDS = 64  # 2048-bit key in 32-bit words
    if n.bit_length() != RSANUMWORDS * 32:
        raise ValueError("adb needs a 2048-bit RSA key")

    r32 = 1 << 32
    n0inv = (-pow(n, -1, r32)) % r32
    rr = pow(2, RSANUMWORDS * 64, n)  # (2^2048)^2 mod n

    def to_words(value: int, count: int) -> list:
        words = []
        for _ in range(count):
            words.append(value & 0xFFFFFFFF)
            value >>= 32
        return words

    buf = struct.pack("<II", RSANUMWORDS, n0inv)
    buf += struct.pack(f"<{RSANUMWORDS}I", *to_words(n, RSANUMWORDS))
    buf += struct.pack(f"<{RSANUMWORDS}I", *to_words(rr, RSANUMWORDS))
    buf += struct.pack("<I", e)

    return base64.b64encode(buf) + b" adbclient\x00"


class AdbAuth:
    def __init__(self, key_path: str = "adbkey"):
        self.key_path: str = key_path
        self.private_key, self.public_key = self._load_or_generate()

    def _load_or_generate(self) -> tuple:
        if Path(self.key_path).exists():
            with open(self.key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(
                    f.read(), password=None, backend=default_backend()
                )
        else:
            private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048, backend=default_backend()
            )
            with open(self.key_path, "wb") as f:
                f.write(
                    private_key.private_bytes(
                        serialization.Encoding.PEM,
                        serialization.PrivateFormat.TraditionalOpenSSL,
                        serialization.NoEncryption(),
                    )
                )
        return private_key, private_key.public_key()

    def sign(self, token: bytes) -> bytes:
        # the token from the device is already a sha1 digest, don't hash it again
        return self.private_key.sign(
            token, padding.PKCS1v15(), utils.Prehashed(hashes.SHA1())
        )

    def public_key_bytes(self) -> bytes:
        return _encode_adb_rsa_pubkey(self.public_key)


class AdbConnection(ABC):
    def __init__(self):
        self.auth: AdbAuth = AdbAuth()
        self.local_id: int = 1
        self.remote_id: int = 0
        self.max_data: int = MAX_PAYLOAD
        self.protocol_version: int = A_VERSION_MIN
        self.banner: str = ""

    def _send_packet(self, packet: AdbPacket, timeout: int = TIMEOUT_MS) -> None:
        if packet.data_len > self.max_data:
            raise ValueError(
                f"Payload {packet.data_len} is over max_data {self.max_data}"
            )
        skip: bool = self.protocol_version >= A_VERSION_SKIP_CHECKSUM
        # adb.c writes the header and the payload as two separate writes
        self._write(packet.header(skip), timeout)
        if packet.data_len:
            self._write(packet.data, timeout)

    def _recv_packet(self, timeout: int = TIMEOUT_MS) -> AdbPacket:
        header: bytes = self._read(24, timeout)
        command, arg0, arg1, data_len, data_check, magic = struct.unpack("<6I", header)
        if magic != (command ^ 0xFFFFFFFF) & 0xFFFFFFFF:
            raise ConnectionError("Bad packet magic")
        if data_len > self.max_data:
            raise ConnectionError(f"Packet too big: {data_len}")
        data: bytes = self._read(data_len, timeout) if data_len else b""
        packet = AdbPacket(command, arg0, arg1, data)
        # modern devices send 0 even in the CNXN reply, before we've negotiated
        if (
            self.protocol_version < A_VERSION_SKIP_CHECKSUM
            and data_check != 0
            and packet.data_crc != data_check
        ):
            raise ConnectionError("Bad data checksum")
        return packet

    def _handshake(self) -> None:
        self._send_packet(AdbPacket(CMD_CNXN, A_VERSION, MAX_PAYLOAD, b"host::\x00"))
        packet = self._recv_packet()

        sent_signature: bool = False
        sent_key: bool = False
        while packet.command == CMD_AUTH:
            if packet.arg0 != AUTH_TOKEN:
                raise ConnectionError(f"Unexpected AUTH arg0: {packet.arg0}")
            if not sent_signature:
                signature = self.auth.sign(packet.data)
                self._send_packet(AdbPacket(CMD_AUTH, AUTH_SIGNATURE, 0, signature))
                sent_signature = True
            elif not sent_key:
                pubkey = self.auth.public_key_bytes()
                self._send_packet(AdbPacket(CMD_AUTH, AUTH_RSAPUBKEY, 0, pubkey))
                sent_key = True
                raise Warning("Check device screen to authorize this computer...")
            else:
                raise ConnectionError("Device rejected our key")
            packet = self._recv_packet(AUTH_TIMEOUT_MS if sent_key else TIMEOUT_MS)

        if packet.command != CMD_CNXN:
            raise ConnectionError(
                f"Handshake failed, got command: {hex(packet.command)}"
            )

        # same negotiation as adb.c: take the lower of the two
        self.protocol_version = min(packet.arg0, A_VERSION)
        self.max_data = min(packet.arg1, MAX_PAYLOAD) or MAX_PAYLOAD
        self.banner = packet.data.decode(errors="replace").rstrip("\x00")
        # print("Handshake complete.")

    def shell(self, command: str) -> str:
        dest: bytes = f"shell:{command}\x00".encode()
        local_id: int = self.local_id
        self.local_id += 1
        self._send_packet(AdbPacket(CMD_OPEN, local_id, 0, dest))
        output: list[bytes] = []
        remote_id: int = 0

        while True:
            packet: AdbPacket = self._recv_packet()
            # skip anything that isn't for our stream
            if packet.arg1 != local_id:
                continue

            if packet.command == CMD_OKAY:
                remote_id = packet.arg0
            elif packet.command == CMD_WRTE:
                remote_id = packet.arg0
                self._send_packet(AdbPacket(CMD_OKAY, local_id, remote_id))
                output.append(packet.data)
            elif packet.command == CMD_CLSE:
                # CLSE before any OKAY means the device refused to open the stream
                if remote_id == 0 and packet.arg0 == 0:
                    raise ConnectionError(f"Device refused to open: {command}")
                self._send_packet(AdbPacket(CMD_CLSE, local_id, packet.arg0))
                break

        return b"".join(output).decode(errors="replace")

    @abstractmethod
    def _write(self, data: bytes, timeout: int) -> None:
        pass

    @abstractmethod
    def _read(self, n: int, timeout: int) -> bytes:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class AdbTcpIpConnect(AdbConnection):
    def __init__(self, host: str, port: int = 5555):
        super().__init__()
        self.sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT_MS / 1000)
        self.sock.connect((host, port))
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        self._handshake()

    def _write(self, data: bytes, timeout: int) -> None:
        self.sock.settimeout(timeout / 1000)
        self.sock.sendall(data)

    def _read(self, n: int, timeout: int) -> bytes:
        self.sock.settimeout(timeout / 1000)
        buf = bytearray()
        while len(buf) < n:
            chunk: bytes = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed")
            buf += chunk
        return bytes(buf)

    def close(self) -> None:
        self.sock.close()


def _find_adb_interface(dev: usb.core.Device) -> tuple:
    # iterating the descriptors doesn't open the device, so this is safe on
    # every usb device in the system, even ones we have no driver for
    try:
        for cfg in dev:
            for intf in cfg:
                ids = (
                    intf.bInterfaceClass,
                    intf.bInterfaceSubClass,
                    intf.bInterfaceProtocol,
                )
                if ids == (ADB_CLASS, ADB_SUBCLASS, ADB_PROTOCOL):
                    return cfg, intf
    except (usb.core.USBError, NotImplementedError, ValueError):
        pass
    return None, None


class AdbUsbConnect(AdbConnection):
    def __init__(self, serial: str | None = None):
        super().__init__()
        self.intf_num: int = 0
        self._detached: bool = False
        self.ep_in: usb.core.Endpoint | None = None
        self.ep_out: usb.core.Endpoint | None = None
        self.dev, cfg, intf = self._find_device(serial)
        try:
            self._setup_endpoints(cfg, intf)
        except usb.core.USBError:
            raise Exception(
                "Please check if `adb` or any other application is accessing the device/port (run `adb kill-server` if you have ADB)"
            )
        self._handshake()

    def _find_device(self, serial: str | None = None) -> tuple:
        backend = DLLHandle().DLLWrap()
        found: list = []
        for d in usb.core.find(find_all=True, backend=backend):
            cfg, intf = _find_adb_interface(d)
            if intf is not None:
                found.append((d, cfg, intf))
        if not found:
            raise ConnectionError("No ADB USB device found")
        if serial:
            for d, cfg, intf in found:
                try:
                    if usb.util.get_string(d, d.iSerialNumber) == serial:
                        return d, cfg, intf
                except (usb.core.USBError, NotImplementedError, ValueError):
                    continue
            raise ConnectionError(f"Device with serial {serial} not found")
        return found[0]

    def _setup_endpoints(self, cfg, intf) -> None:
        self.intf_num = intf.bInterfaceNumber

        try:
            active: int = self.dev.get_active_configuration().bConfigurationValue
        except (usb.core.USBError, NotImplementedError):
            active = None
        if active != cfg.bConfigurationValue:
            self.dev.set_configuration(cfg.bConfigurationValue)

        if platform.system() == "Linux":
            try:
                if self.dev.is_kernel_driver_active(self.intf_num):
                    self.dev.detach_kernel_driver(self.intf_num)
                    self._detached = True
            except usb.core.USBError as e:
                raise ConnectionError(
                    f"Couldn't detach kernel driver from interface {self.intf_num}: {e}"
                ) from e

        try:
            usb.util.claim_interface(self.dev, self.intf_num)
        except usb.core.USBError as e:
            raise ConnectionError(
                f"Couldn't claim ADB interface {self.intf_num}: {e}. "
                "Kill any running adb server, and on windows make sure the device uses WinUSB."
            ) from e

        if intf.bAlternateSetting:
            self.dev.set_interface_altsetting(self.intf_num, intf.bAlternateSetting)

        def bulk(direction: int):
            return usb.util.find_descriptor(
                intf,
                custom_match=lambda e: (
                    usb.util.endpoint_direction(e.bEndpointAddress) == direction
                    and usb.util.endpoint_type(e.bmAttributes)
                    == usb.util.ENDPOINT_TYPE_BULK
                ),
            )

        self.ep_out = bulk(usb.util.ENDPOINT_OUT)
        self.ep_in = bulk(usb.util.ENDPOINT_IN)
        if self.ep_out is None or self.ep_in is None:
            raise ConnectionError("Could not locate ADB bulk endpoints")

    def _write(self, data: bytes, timeout: int) -> None:
        try:
            self.ep_out.write(data, timeout=timeout)
            # transfer ended exactly on a packet boundary, device needs a zero length packet
            if len(data) % self.ep_out.wMaxPacketSize == 0:
                self.ep_out.write(b"", timeout=timeout)
        except usb.core.USBError as e:
            if e.errno == 32:
                self.ep_out.clear_halt()
            raise

    def _read(self, n: int, timeout: int) -> bytes:
        buf = bytearray()
        while len(buf) < n:
            try:
                chunk = bytes(self.ep_in.read(n - len(buf), timeout=timeout))
            except usb.core.USBError as e:
                if e.errno == 32:
                    self.ep_in.clear_halt()
                raise
            buf += chunk
        return bytes(buf)

    def close(self) -> None:
        try:
            usb.util.release_interface(self.dev, self.intf_num)
        except usb.core.USBError:
            pass
        if self._detached:
            try:
                self.dev.attach_kernel_driver(self.intf_num)
            except usb.core.USBError:
                pass
        usb.util.dispose_resources(self.dev)
