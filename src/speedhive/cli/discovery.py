"""Auto‑discovery of exporter/processor/analyzer modules."""

import importlib
import pkgutil

MAPPING = {
    # Aliases: new module-derived names -> explicit CLI names (causes discovery to skip duplicates)
    "analyze-consistency": "report-consistency",
    "analyze-driver-laps": "extract-driver-laps",
    "process-sqlite-import": "to-sqlite",
    "process-track-records": "extract-track-records",
    "export-org-cache": "refresh-org-cache",
}

def discover_modules():
    found = []
    for pkg_name, category in (
        ("speedhive.exporters", "exporters"),
        ("speedhive.processing", "processing"),
        ("speedhive.analyzers", "analyzers"),
    ):
        try:
            pkg = importlib.import_module(pkg_name)
        except Exception:
            continue
        if not hasattr(pkg, "__path__"):
            continue
        for finder, name, ispkg in pkgutil.iter_modules(pkg.__path__):
            full_name = f"{pkg_name}.{name}"
            try:
                mod = importlib.import_module(full_name)
            except Exception:
                continue
            if hasattr(mod, "main") and callable(getattr(mod, "main")):
                cmd = name.replace("_", "-")
                cmd = MAPPING.get(cmd, cmd)
                found.append((cmd, mod, category))
    return found

def register_discovered(subparsers):
    for cmd, mod, cat in discover_modules():
        if cmd in subparsers.choices:
            continue
        if hasattr(mod, "register_subparser") and callable(getattr(mod, "register_subparser")):
            try:
                sp = subparsers.add_parser(cmd, help=f"{cat} ({cmd})")
            except Exception:
                # If add_parser fails (e.g. conflicting name already added), skip or handle
                continue
            try:
                mod.register_subparser(sp)
                sp.set_defaults(_module=mod)
            except Exception as e:
                # Print exception or log it to help debugging
                import traceback
                print(f"Error registering subparser for {cmd}: {e}")
                traceback.print_exc()
                sp.add_argument("extra_args", nargs="*")
                sp.set_defaults(_module=mod)
        else:
            try:
                sp = subparsers.add_parser(cmd, help=f"{cat} ({cmd})")
                sp.add_argument("extra_args", nargs="*")
                sp.set_defaults(_module=mod)
            except Exception:
                continue
