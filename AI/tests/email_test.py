import sys
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(current_dir))

from AI.tasks import send_email

send_email("Hello, world!", "Test", "morgannstuart@gmail.com")