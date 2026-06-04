import pytest
from config_profiles import ConfigProfiles, HardwareProfile

@pytest.fixture
def temp_profiles(tmp_path): return ConfigProfiles(profiles_dir=str(tmp_path / "profiles"))

class TestHardwareProfile:
    def test_create(self):
        p = HardwareProfile(name="test", board_fqbn="arduino:avr:nano")
        assert p.name == "test"
    def test_to_dict(self):
        p = HardwareProfile(name="test", board_fqbn="esp32:esp32:esp32dev", baudrate=9600)
        assert p.to_dict()["baudrate"] == 9600
    def test_from_dict(self):
        assert HardwareProfile.from_dict({"name": "t", "board_fqbn": "arduino:avr:uno"}).name == "t"

class TestConfigProfiles:
    def test_default_exists(self, temp_profiles):
        assert temp_profiles.get_profile("default") is not None
    def test_create_profile(self, temp_profiles):
        assert temp_profiles.create_profile("esp32-t", "esp32:esp32:esp32dev", board_name="ESP32")["status"] == "created"
        assert temp_profiles.get_profile("esp32-t")["board_fqbn"] == "esp32:esp32:esp32dev"
    def test_list_profiles(self, temp_profiles):
        temp_profiles.create_profile("t1", "arduino:avr:uno")
        assert temp_profiles.list_profiles()["count"] >= 2
    def test_update_profile(self, temp_profiles):
        temp_profiles.create_profile("t2", "arduino:avr:nano")
        assert temp_profiles.update_profile("t2", baudrate=9600)["status"] == "updated"
    def test_delete_profile(self, temp_profiles):
        temp_profiles.create_profile("del", "arduino:avr:uno")
        assert temp_profiles.delete_profile("del")["status"] == "deleted"
    def test_delete_default(self, temp_profiles):
        assert temp_profiles.delete_profile("default")["status"] == "error"
    def test_set_active(self, temp_profiles):
        temp_profiles.create_profile("active", "esp32:esp32:esp32dev")
        assert temp_profiles.set_active("active")["status"] == "active"
        assert temp_profiles.get_active() == "active"
