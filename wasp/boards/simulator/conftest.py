import glob
import importlib
import inspect

try:
    import tomllib
except ImportError:  # pragma: no cover — container is 3.12+
    import tomli as tomllib


def _toml_watchface_modules():
    """Module names for [[watchface]] entries in wasp.toml (this firmware's faces)."""
    with open('wasp.toml', 'rb') as config_file:
        config = tomllib.load(config_file)
    names = []
    for face in config.get('watchface') or []:
        path = face.get('file')
        if not path or not path.endswith('.py'):
            continue
        names.append(path[:-3].replace('/', '.'))
    return names


def discover_app_constructors():
    apps = []
    appClasses = []

    globs_system = glob.glob('wasp/apps/system/*.py')
    names_system = [g[5:-3].replace('/', '.') for g in globs_system]
    globs_user = glob.glob('apps/*.py')
    names_user = [g[:-3].replace('/', '.') for g in globs_user]
    # Do not glob every file under watch_faces/: unused faces (e.g. week_clock)
    # import apps.user.clock, which is only generated when clock.py is in toml.
    names_watchface = _toml_watchface_modules()
    modules = [importlib.import_module(n) for n in names_system + names_user + names_watchface]

    for m in modules:
        for sym in m.__dict__.keys():
            if len(sym) > 3 and sym[-3:] == 'App' and not sym in appClasses:
                constructor = m.__dict__[sym]
                sig = inspect.signature(constructor)
                if len(sig.parameters) == 0:
                    apps.append(constructor)
                    appClasses.append(sym)

    return apps


def pytest_generate_tests(metafunc):
    if 'constructor' in metafunc.fixturenames:
        metafunc.parametrize('constructor', discover_app_constructors())
