"""The repository's shipped configuration is usable without migrating its history."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from tools.workflow_lib.topic_service import read_config
from tools.workflow_lib.tickets import frontmatter

ROOT = Path(__file__).resolve().parents[1]

class RepositoryConfigurationTests(unittest.TestCase):
    def test_repository_configuration_matches_declared_full_tests(self):
        config = read_config(ROOT)
        self.assertEqual(('local', 'shared', 'main', 'auto', 'standard'),
                         tuple(config[k] for k in ('task_backend', 'agent_directory_mode',
                               'default_base_branch', 'default_execution_agent', 'assurance_level')))
        self.assertTrue(config['test_commands'])
        for ticket in (ROOT / '.agent/work/workflow-simplification/tickets').glob('*.md'):
            self.assertEqual(config['test_commands'], frontmatter(ticket)['test_commands'], str(ticket))
        for key in ('standards_sources', 'domain_sources'):
            for source in config[key]:
                self.assertTrue((ROOT / source).is_file(), source)
        preview = subprocess.run([sys.executable, str(ROOT / 'tools/workflow.py'),
                                  'setup', '--repo', str(ROOT)], capture_output=True, text=True)
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertEqual(config, json.loads(preview.stdout)['config'])
