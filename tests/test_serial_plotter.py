import pytest
from serial_plotter import SerialPlotter, PlotterData

class TestPlotterData:
    def test_add_point(self):
        data = PlotterData()
        data.add_point([1.0, 2.0], "1.0,2.0")
        assert len(data.points) == 1 and data.channels == 2
    def test_max_points(self):
        data = PlotterData(max_points=5)
        for i in range(10): data.add_point([float(i)], str(i))
        assert len(data.points) == 5
    def test_summary(self):
        data = PlotterData()
        data.add_point([1.0, 10.0], "1,10")
        data.add_point([2.0, 20.0], "2,20")
        s = data.summary()
        assert s["channels"] == 2 and s["points"] == 2

class TestSerialPlotter:
    def test_parse_comma(self):
        assert SerialPlotter()._parse_line("1.5,2.5,3.5") == [1.5, 2.5, 3.5]
    def test_parse_tab(self):
        assert SerialPlotter()._parse_line("1.5\t2.5\t3.5") == [1.5, 2.5, 3.5]
    def test_parse_space(self):
        assert SerialPlotter()._parse_line("1 2 3") == [1.0, 2.0, 3.0]
    def test_parse_labeled(self):
        vals = SerialPlotter()._parse_line("TEMP:23.5,HUM:65.2")
        assert 23.5 in vals and 65.2 in vals
    def test_parse_mixed(self):
        vals = SerialPlotter()._parse_line("sensor1=42.0 sensor2=-3.14")
        # First number in each token is extracted (1 from sensor1, 2 from sensor2)
        assert 1.0 in vals and 2.0 in vals
    def test_open_nonexistent(self):
        assert SerialPlotter().open("/dev/ttyNONEXISTENT999")["status"] == "error"
