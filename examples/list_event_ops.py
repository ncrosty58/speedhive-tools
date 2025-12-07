
# examples/list_event_ops.py
import pkgutil
import event_results_client.api.event_controller as ec

print("Submodules under event_controller:")
for m in pkgutil.iter_modules(ec.__path__):
    print(" -", m.name)
