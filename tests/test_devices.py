"""Tests for src/devices.py — DeviceInfo schema and discovery helpers."""

from devices import DeviceInfo, discover_devices_json


class TestDeviceInfo:
    def test_rfcomm_channel_field(self):
        # Field was renamed from rfcord_channel → rfcomm_channel in v0.2.2.
        dev = DeviceInfo(device_id="bt:test", device_type="bluetooth", path="rfcomm:00")
        assert dev.rfcomm_channel == 1
        assert not hasattr(dev, "rfcord_channel")

    def test_to_dict_contains_renamed_field(self):
        dev = DeviceInfo(
            device_id="bt:test",
            device_type="bluetooth",
            path="rfcomm:00",
            rfcomm_channel=2,
        )
        d = dev.to_dict()
        assert d["rfcomm_channel"] == 2


class TestDiscovery:
    def test_discover_returns_structured(self):
        # Just ensures the discovery shim doesn't raise even if no devices.
        result = discover_devices_json()
        assert "devices" in result
        assert "total_count" in result
        assert isinstance(result["devices"], list)
