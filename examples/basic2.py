
from speedhive_tools import Speedhive

sh = Speedhive()
events = sh.events(count=5, offset=0)
print("Events:", len(events))
print("First:", events[0] if events else None)
