"""Auto‑discovery of exporter/processor/analyzer modules."""

import importlib
import pkgutil

def discover_modules():
    found = []
    for pkg_name, category in (
        ("speedhive.exporters", "exporters"),
        ("speedhive.processors", "processors"),
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
                found.append((cmd, mod, category))
    return found

def register_discovered(subparsers):
    for cmd, mod, cat in discover_modules():
        if hasattr(mod, "register_subparser") and callable(getattr(mod, "register_subparser")):
            try:
                sp = subparsers.add_parser(cmd, help=f"{cat} ({cmd})")
                mod.register_subparser(sp)
                sp.set_defaults(_module=mod)
            except Exception:
                sp = subparsers.add_parser(cmd, help=f"{cat} ({cmd})")
                sp.add_argument("extra_args", nargs="*")
                sp.set_defaults(_module=mod)
        else:
            sp = subparsers.add_parser(cmd, help=f"{cat} ({cmd})")
            sp.add_argument("extra_args", nargs="*")
            sp.set_defaults(_module=mod)
