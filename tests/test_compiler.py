import pytest
from compiler import BOARD_CONFIGS, CompileResult, UploadResult

class TestBoardConfigs:
    def test_avr_nano_exists(self):
        assert "nano" in BOARD_CONFIGS
        assert BOARD_CONFIGS["nano"]["fqbn"] == "arduino:avr:nano"
    def test_esp32_exists(self):
        assert "esp32" in BOARD_CONFIGS
        assert BOARD_CONFIGS["esp32"]["fqbn"].startswith("esp32:")
    def test_esp8266_exists(self):
        assert "esp8266" in BOARD_CONFIGS
        assert BOARD_CONFIGS["esp8266"]["fqbn"].startswith("esp8266:")
    def test_rp2040_exists(self):
        assert "rp2040" in BOARD_CONFIGS
        assert BOARD_CONFIGS["rp2040"]["fqbn"].startswith("rp2040:")
    def test_all_configs_have_fqbn(self):
        for name, config in BOARD_CONFIGS.items():
            assert "fqbn" in config, f"Board {name} missing fqbn"
            assert ":" in config["fqbn"], f"Board {name} fqbn invalid"
    def test_all_configs_have_cpu(self):
        for name, config in BOARD_CONFIGS.items():
            assert "cpu" in config, f"Board {name} missing cpu"

class TestCompileResult:
    def test_to_dict(self):
        result = CompileResult(success=True, output="ok", size_bytes=1234)
        d = result.to_dict()
        assert d["success"] is True and d["size_bytes"] == 1234

class TestUploadResult:
    def test_to_dict(self):
        result = UploadResult(success=True, message="done")
        assert result.to_dict()["success"] is True

class TestCompileSketch:
    def test_nonexistent_file(self):
        from compiler import compile_sketch
        result = compile_sketch("/tmp/does_not_exist_12345.ino")
        assert result.success is False
