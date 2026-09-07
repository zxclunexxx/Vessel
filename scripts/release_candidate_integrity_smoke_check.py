from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
index = (root / 'index.html').read_text(encoding='utf-8')
android = (root / '.github' / 'workflows' / 'android-apk.yml').read_text(encoding='utf-8')
windows = (root / '.github' / 'workflows' / 'windows-exe.yml').read_text(encoding='utf-8')

cdn_versions = re.findall(r'@supabase/supabase-js@(\d+\.\d+\.\d+)', index)
if len(cdn_versions) != 1:
    raise SystemExit('Supabase browser SDK must be pinned to exactly one semantic version')
if '@supabase/supabase-js@2"></script>' in index:
    raise SystemExit('Floating Supabase major-version CDN dependency is still present')

required_android = [
    'android-apk.sha256',
    'android-apk-metadata.txt',
    'build_variant=debug',
    'signing=android-debug-certificate',
    'production_ready=false',
]
for marker in required_android:
    if marker not in android:
        raise SystemExit(f'Android RC integrity marker missing: {marker}')

required_windows = [
    'Get-FileHash',
    'Get-AuthenticodeSignature',
    'windows-exe.sha256',
    'windows-exe-metadata.txt',
    'authenticode_status=',
    'production_ready=',
]
for marker in required_windows:
    if marker not in windows:
        raise SystemExit(f'Windows RC integrity marker missing: {marker}')

print(f'Release candidate integrity smoke check passed (Supabase JS {cdn_versions[0]})')
