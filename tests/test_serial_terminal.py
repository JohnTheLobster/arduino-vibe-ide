import pytest
from serial_terminal import SerialTerminal

class TestSerialTerminal:
    def test_init(self):
        term = SerialTerminal()
        assert not term.connected and term.path == ""
    def test_open_nonexistent(self):
        term = SerialTerminal()
        assert term.open("/dev/ttyNONEXISTENT999")["status"] == "error"
    def test_write_disconnected(self):
        assert SerialTerminal().write("hello")["status"] == "disconnected"
    def test_read_disconnected(self):
        assert SerialTerminal().read(1024)["status"] == "disconnected"
    def test_close_disconnected(self):
        assert SerialTerminal().close()["status"] == "closed"
    def test_check_connection(self):
        assert "connected" in SerialTerminal().check_connection()
    def test_retry_write(self):
        result = SerialTerminal().retry_write("hello", retries=1)
        assert result["status"] in ("disconnected", "error")
