"""Engine registry. Drop a module in this package that defines ENGINE = SomeEngine()."""
import importlib
import pkgutil

REGISTRY = {}

for m in pkgutil.iter_modules(__path__):
    if m.name == "base":
        continue
    mod = importlib.import_module(f"{__name__}.{m.name}")
    eng = getattr(mod, "ENGINE", None)
    if eng is not None:
        REGISTRY[eng.name] = eng


def get(name):
    return REGISTRY.get(name) or REGISTRY["title"]
