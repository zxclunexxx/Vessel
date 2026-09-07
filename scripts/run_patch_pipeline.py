from pathlib import Path
import subprocess
import sys

scripts_dir = Path(__file__).resolve().parent
repo_dir = scripts_dir.parent

# Patch scripts are immutable, one-shot migrations. Replaying every historical patch against
# modern source makes the pipeline slower and causes false failures when newer guards legitimately
# supersede an old exact-text anchor. Only patch migrations newly added on the sprint branch are
# executable; committed main already contains and Fast Gate verifies all historical migrations.
subprocess.run(
    ['git', 'fetch', '--no-tags', 'origin', 'main'],
    cwd=repo_dir,
    check=True,
    stdout=subprocess.DEVNULL,
)
merge_base = subprocess.check_output(
    ['git', 'merge-base', 'origin/main', 'HEAD'],
    cwd=repo_dir,
    text=True,
).strip()
if not merge_base:
    raise SystemExit('Unable to resolve merge-base with origin/main')

changed = subprocess.check_output(
    ['git', 'diff', '--diff-filter=A', '--name-only', merge_base, 'HEAD', '--', 'scripts/*_patch.py'],
    cwd=repo_dir,
    text=True,
).splitlines()

ordered = []
for relative in sorted(set(changed)):
    path = repo_dir / relative
    if path.parent != scripts_dir or not path.name.endswith('_patch.py') or not path.is_file():
        raise SystemExit(f'Unsafe or missing autonomous patch path: {relative}')
    ordered.append(path)

if not ordered:
    print('Vessel patch pipeline: no new patch migrations relative to main')
    raise SystemExit(0)

print(f'Vessel patch pipeline: {len(ordered)} new migration(s) relative to {merge_base[:12]}')
for path in ordered:
    print(f'  - {path.name}')

for path in ordered:
    print(f'\n=== {path.name} ===', flush=True)
    subprocess.run([sys.executable, str(path)], cwd=repo_dir, check=True)

print('\nVessel patch pipeline completed successfully')
