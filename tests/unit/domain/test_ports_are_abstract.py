import inspect
from abc import ABC, abstractmethod
from mim.mcm.domain.ports import IdentityRepository, VersionRepository, SourceRepository, IndexPublisher, SourceResolver
from mim.mcl.domain.ports import DeviceRepository, SessionRepository, PermissionService

def test_ports_are_abstract():
    ports = [
        IdentityRepository,
        VersionRepository,
        SourceRepository,
        IndexPublisher,
        SourceResolver,
        DeviceRepository,
        SessionRepository,
        PermissionService,
    ]
    for port in ports:
        assert inspect.isabstract(port), f"{port.__name__} should be abstract"
