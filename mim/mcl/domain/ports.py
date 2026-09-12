from abc import ABC, abstractmethod
from .device import Device
from .session import Session
from .permission import Subject

class DeviceRepository(ABC):
    @abstractmethod
    def get(self, device_id: str) -> Device: ...
    @abstractmethod
    def add(self, device: Device) -> None: ...

class SessionRepository(ABC):
    @abstractmethod
    def get(self, session_id: str) -> Session: ...
    @abstractmethod
    def add(self, session: Session) -> None: ...

class PermissionService(ABC):
    @abstractmethod
    def check_permission(self, subject: Subject, action: str, resource: str) -> bool: ...
