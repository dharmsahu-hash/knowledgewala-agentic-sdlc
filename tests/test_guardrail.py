"""Regression tests for scripts/block_destructive.py. Run: python -m unittest discover -s tests"""
import json
import os
import subprocess
import sys
import unittest

HOOK = os.path.join(os.path.dirname(__file__), "..", "scripts", "block_destructive.py")
sys.path.insert(0, os.path.dirname(HOOK))
import block_destructive as g  # noqa: E402

# Commands are assembled so this file itself never contains a runnable destructive line.
RM, GIT = "r" + "m", "gi" + "t"

BLOCK = [
    f"{RM} -rf /x", f"{RM} -fr x", f"{RM} foo -rf", f"{RM} -r dir", f"{RM} -R dir", f"{RM} --recursive --force d",
    f"echo hi && {RM} -fr d", f"sudo {RM} -rf /", "Remove-Item x -Recurse -Force", "ri -r x", f"del /s /q x",
    "find . -name '*.tmp' -delete", f"{GIT} push --force origin main", f"{GIT} push -f", f"{GIT} push origin +main",
    f"{GIT} push --force-with-lease", f"{GIT} reset --hard HEAD~1", f"{GIT} clean -fd", f"{GIT} branch -D old",
    f"{GIT} checkout -- .", "terraform apply", "terraform destroy -auto-approve", "kubectl delete pod x", "kubectl apply -f a.yaml",
    "aws s3 rm s3://b/k", "aws --profile p s3 rm s3://b", "aws ec2 terminate-instances --instance-ids i-1",
    "aws s3api delete-bucket --bucket b", "psql -c 'DROP TABLE a'", 'mysql -e "delete from users"',
    "python -c \"import shutil; shutil.rmtree('x')\"", "dd if=/dev/zero of=/dev/sda", "mkfs.ext4 /dev/sda1",
]
ALLOW = [
    f"{RM} -f a.txt", f"{RM} a.txt", "ls -la", "git status", "git push origin main", "git push --dry-run",
    "git branch -d merged", "git checkout main", "git checkout -- file.txt", "git clean -n",
    "npm test", "python -m pytest", "aws s3 ls", "aws s3 ls | grep rm", "aws ec2 describe-instances",
    "kubectl get pods", "kubectl apply -f a.yaml --dry-run=client", "terraform plan",
    'git commit -m "delete from users; rm -rf is bad"', "echo 'terraform apply' > note.txt",
    "grep -n 'DROP TABLE' schema.sql", "cat <<'EOF'\nrm -rf /\nEOF", "find . -name '*.py'", "psql -c 'select 1'",
]


class Guardrail(unittest.TestCase):
    def test_blocks(self):
        for c in BLOCK:
            with self.subTest(cmd=c):
                self.assertIsNotNone(g.check(c), f"should block: {c}")

    def test_allows(self):
        for c in ALLOW:
            with self.subTest(cmd=c):
                self.assertIsNone(g.check(c), f"should allow: {c}")

    def run_hook(self, stdin):
        return subprocess.run([sys.executable, "-I", HOOK], input=stdin, text=True, capture_output=True)

    def test_exit_codes_via_stdin(self):
        r = self.run_hook(json.dumps({"tool_input": {"command": f"{RM} -rf /x"}}))
        self.assertEqual(r.returncode, 2)
        self.assertIn("guardrail", r.stderr)
        r = self.run_hook(json.dumps({"tool_input": {"command": "ls"}}))
        self.assertEqual(r.returncode, 0)

    def test_fails_open_on_garbage(self):
        for bad in ("garbage", "", "{}", '{"tool_input": {"command": 5}}'):
            self.assertEqual(self.run_hook(bad).returncode, 0, bad)


if __name__ == "__main__":
    unittest.main()
