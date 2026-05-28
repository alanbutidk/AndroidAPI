import os;os.system("") #To enable VT on windows (Basically color support on windows)
import struct
import socket
import usb.core
import usb.util
from abc import ABC, abstractmethod
from pathlib import Path
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

CMD_CNXN: int = 0x4e584e43
CMD_OPEN: int = 0x4e45504f
CMD_WRTE: int = 0x45545257
CMD_CLSE: int = 0x45534c43
CMD_AUTH: int = 0x48545541

AUTH_TOKEN:     int = 1
AUTH_SIGNATURE: int = 2
AUTH_RSAPUBKEY: int = 3

ADB_VERSION: int = 0x01000000
MAX_DATA:    int = 1024 * 1024


class AdbPacket:
    def __init__(self, command: int, arg0: int, arg1: int, data: bytes = b""):
        self.command: int   = command
        self.arg0:    int   = arg0
        self.arg1:    int   = arg1
        self.data:    bytes = data if isinstance(data, bytes) else data.encode()

    def encode(self) -> bytes:
        data_crc: int = sum(self.data) & 0xFFFFFFFF
        magic:    int = self.command ^ 0xFFFFFFFF
        header: bytes = struct.pack(
            "<IIIIII",
            self.command,
            self.arg0,
            self.arg1,
            len(self.data),
            data_crc,
            magic
        )
        return header + self.data

    @staticmethod
    def decode(raw: bytes) -> "AdbPacket":
        if len(raw) < 24:
            raise ValueError("Packet too short")
        command, arg0, arg1, data_len, data_crc, magic = struct.unpack("<IIIIII", raw[:24])
        data: bytes = raw[24:24 + data_len]
        return AdbPacket(command, arg0, arg1, data)


class AdbAuth:
    def __init__(self, key_path: str = "adbkey"):
        self.key_path: str = key_path
        self.private_key, self.public_key = self._load_or_generate()

    def _load_or_generate(self) -> tuple:
        if Path(self.key_path).exists():
            with open(self.key_path, "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            with open(self.key_path, "wb") as f:
                f.write(private_key.private_bytes(
                    serialization.Encoding.PEM,
                    serialization.PrivateFormat.TraditionalOpenSSL,
                    serialization.NoEncryption()
                ))
        public_key = private_key.public_key()
        return private_key, public_key

    def sign(self, token: bytes) -> bytes:
        return self.private_key.sign(token, padding.PKCS1v15(), hashes.SHA1())

    def public_key_bytes(self) -> bytes:
        return self.public_key.public_bytes(
            serialization.Encoding.DER,
            serialization.PublicFormat.SubjectPublicKeyInfo
        )


class AdbConnection(ABC):
    def __init__(self):
        self.auth:      AdbAuth = AdbAuth()
        self.local_id:  int     = 1
        self.remote_id: int     = None

    def _handshake(self) -> None:
        cnxn: AdbPacket = AdbPacket(CMD_CNXN, ADB_VERSION, MAX_DATA, b"host::AndroidAPI\x00")
        self._send_packet(cnxn)
        while True:
            packet: AdbPacket = self._recv_packet()
            if packet.command == CMD_AUTH:
                if packet.arg0 == AUTH_TOKEN:
                    sig: bytes = self.auth.sign(packet.data)
                    self._send_packet(AdbPacket(CMD_AUTH, AUTH_SIGNATURE, 0, sig))
                elif packet.arg0 == AUTH_RSAPUBKEY:
                    self._send_packet(AdbPacket(CMD_AUTH, AUTH_RSAPUBKEY, 0, self.auth.public_key_bytes()))
            elif packet.command == CMD_CNXN:
                break

    def shell(self, command: str) -> str:
        dest:     bytes = f"shell:{command}\x00".encode()
        local_id: int   = self.local_id
        self.local_id += 1
        self._send_packet(AdbPacket(CMD_OPEN, local_id, 0, dest))
        output: list[str] = []
        while True:
            packet: AdbPacket = self._recv_packet()
            if packet.command == CMD_WRTE:
                self._send_packet(AdbPacket(CMD_CLSE, local_id, packet.arg0))
                output.append(packet.data.decode(errors="replace"))
            elif packet.command == CMD_CLSE:
                break
        return "".join(output)

    @abstractmethod
    def _send_packet(self, packet: AdbPacket) -> None:
        pass

    @abstractmethod
    def _recv_packet(self) -> AdbPacket:
        pass

    @abstractmethod
    def close(self) -> None:
        pass


class AdbTcpIpConnect(AdbConnection):
    def __init__(self, host: str, port: int = 5555):
        super().__init__()
        self.sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self._handshake()

    def _send_packet(self, packet: AdbPacket) -> None:
        self.sock.sendall(packet.encode())

    def _recv_packet(self) -> AdbPacket:
        header: bytes = self._recv_exactly(24)
        _, _, _, data_len, _, _ = struct.unpack("<IIIIII", header)
        data: bytes = self._recv_exactly(data_len)
        return AdbPacket.decode(header + data)

    def _recv_exactly(self, n: int) -> bytes:
        buf: bytes = b""
        while len(buf) < n:
            chunk: bytes = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("Socket closed")
            buf += chunk
        return buf

    def close(self) -> None:
        self.sock.close()


class AdbUsbConnect(AdbConnection):
    def __init__(self, serial: str = None):
        super().__init__()
        self.dev                  = self._find_device(serial)
        self.ep_in:  usb.core.Endpoint = None
        self.ep_out: usb.core.Endpoint = None
        self._setup_endpoints()
        self._handshake()

    def _find_device(self, serial: str = None) -> usb.core.Device:
        devices: list = list(usb.core.find(find_all=True, idVendor=0x18D1))
        if not devices:
            raise ConnectionError("No ADB USB device found")
        if serial:
            for d in devices:
                if usb.util.get_string(d, d.iSerialNumber) == serial:
                    return d
            raise ConnectionError(f"Device with serial {serial} not found")
        return devices[0]

    def _setup_endpoints(self) -> None:
        cfg  = self.dev.get_active_configuration()
        intf = cfg[(0, 0)]
        self.ep_out = usb.util.find_descriptor(intf, custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_OUT)
        self.ep_in  = usb.util.find_descriptor(intf, custom_match=lambda e:
            usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN)

    def _send_packet(self, packet: AdbPacket) -> None:
        self.ep_out.write(packet.encode())

    def _recv_packet(self) -> AdbPacket:
        header: bytes = bytes(self.ep_in.read(24))
        _, _, _, data_len, _, _ = struct.unpack("<IIIIII", header)
        data: bytes   = bytes(self.ep_in.read(data_len)) if data_len > 0 else b""
        return AdbPacket.decode(header + data)

    def close(self) -> None:
        usb.util.dispose_resources(self.dev)
