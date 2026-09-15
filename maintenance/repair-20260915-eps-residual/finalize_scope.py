"""交接前核对工作树白名单、原输入与受保护文件；不提交。"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True).stdout


def digest(path):
    return hashlib.sha256((ROOT/path).read_bytes()).hexdigest()


tracked = git('diff', '--name-only', 'HEAD').decode().splitlines()
others = git('ls-files', '--others', '--exclude-standard').decode().splitlines()
allowed = {'CHANGELOG.md', 'SKILL.md', 'VERSION', 'pyproject.toml',
           'references/scan-schemas.md', 'scripts/report/entity_source_trace.py',
           'scripts/tests/test_entity_source_trace.py'}
outside = [p for p in tracked+others if p not in allowed
           and not p.startswith('maintenance/repair-20260915-eps-residual/')]
head = git('rev-parse', 'HEAD').decode().strip()
previous = json.loads((OUT/'scope_checks.json').read_text())
protected = {p: digest(p) == v['sha256'] and (ROOT/p).read_bytes() == git('show', 'HEAD:'+p)
             for p,v in previous.items() if isinstance(v,dict) and 'sha256' in v}
production = digest('scripts/report/entity_source_trace.py')
test = digest('scripts/tests/test_entity_source_trace.py')
assert head == '2000b6e78f790ee0ed348cc2ecb8eae796d5136e'
assert not outside and set(tracked) == allowed and all(protected.values())
assert production == 'e85acee4e9a98a664d9b4881ca33177003aa9455261109a01e111e6faeda3cd1'
assert test == '6a23965e085fd48457ffa402f38a0345ae06610e840ad6d42ddc05c93992c3e2'
git('diff','--check')
staging = json.loads((OUT/'followup_staging_checks.json').read_text())
assert [x['ok_count'] for x in staging] == [33,1,2]
assert all(x['exit_code'] == 0 for x in staging)
report = {'head':head,'commit_created':False,'outside_whitelist':outside,
          'modified_tracked':tracked, 'production_sha256':production,'test_sha256':test,
          'protected_files_unchanged':protected,
          'post_suite_production_and_test_sha256_unchanged':True,
          'git_diff_check_exit_code':0,'staging_checks':[33,1,2]}
(OUT/'final_scope_checks.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
