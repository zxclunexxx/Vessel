from pathlib import Path

# Keep the full historical runtime smoke suite, but translate the two attachment-context
# expectations that intentionally changed when uploads were bound to a captured destination.
source_path = Path('scripts/runtime_smoke_check.py')
source = source_path.read_text(encoding='utf-8')

replacements = {
    '    "context=`dm/${activeDmId}`",\n': '    "async function uploadVesselFile(file, user, context)",\n',
    '    "context=`channel/${activeChannelId}`",\n': '    "const attachmentContext=targetDmId?`dm/${targetDmId}`:`channel/${targetChannelId}`;",\n',
}
for old, new in replacements.items():
    if old not in source:
        raise SystemExit(f'Runtime smoke compatibility anchor missing: {old.strip()}')
    source = source.replace(old, new, 1)

namespace = {'__name__': '__main__'}
exec(compile(source, str(source_path), 'exec'), namespace, namespace)
