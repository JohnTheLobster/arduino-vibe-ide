import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def project_root(): return Path(__file__).parent.parent

@pytest.fixture
def sample_sketch(tmp_path):
    sketch = tmp_path / "test.ino"
    sketch.write_text("void setup() { pinMode(13, OUTPUT); } void loop() { digitalWrite(13, HIGH); delay(1000); digitalWrite(13, LOW); delay(1000); }")
    return sketch
