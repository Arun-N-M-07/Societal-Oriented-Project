"""Run a script against a frozen copy of the code, so evaluations measure exactly that copy while the working tree
changes. The repository's .env is loaded into this process's environment (values are never printed); variables
already set (DATABASE_URL for staging) win. The snapshot's `backend` is imported first, so scripts that put the
repository on sys.path still use the snapshot's code. The repository's `backend` is a namespace package, whose path
would follow sys.path; the snapshot copy carries an empty backend/__init__.py (snapshot only) to pin it.
    snapshot_run.py <snapshot root> <script.py> [args...]"""
import os, runpy, sys
from dotenv import load_dotenv

root, script = os.path.abspath(sys.argv[1]), sys.argv[2]
if not os.path.isfile(os.path.join(root, "backend", "__init__.py")):
    sys.exit("snapshot needs backend/__init__.py")
load_dotenv("/Users/arunnm/Projects/SOP/.env")
sys.path.insert(0, root)
import backend  # noqa: E402  (pins the package to the snapshot)
assert os.path.dirname(os.path.abspath(backend.__file__)) == os.path.join(root, "backend"), backend.__file__
os.chdir(root)
sys.argv = [script, *sys.argv[3:]]
runpy.run_path(script, run_name="__main__")
