import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.embedding_tool import EmbeddingSemanticSearchTool, EmbeddingToolInput

FIXTURE_REPO = str(Path(__file__).resolve().parent / "fixtures" / "sample_repo")
CONTEXT_ROOT = Path(__file__).resolve().parent / ".tmp_context"


class TestEmbeddingSemanticSearchTool(unittest.TestCase):

    def setUp(self):
        self.context_dir = CONTEXT_ROOT / self._testMethodName
        shutil.rmtree(self.context_dir, ignore_errors=True)
        self.tool = EmbeddingSemanticSearchTool(context_dir=str(self.context_dir))

    def tearDown(self):
        shutil.rmtree(self.context_dir, ignore_errors=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(CONTEXT_ROOT, ignore_errors=True)

    def test_tool_metadata(self):
        """Verify tool name, description, and schema inheritance."""
        self.assertEqual(self.tool.name, "embedding_semantic_search")
        self.assertEqual(self.tool.args_schema, EmbeddingToolInput)

    def test_input_schema_defaults(self):
        parsed = EmbeddingToolInput(action="search", query="JWT verification")
        self.assertEqual(parsed.mode, "baseline")
        self.assertEqual(parsed.repo_paths, ["repo"])
        self.assertEqual(parsed.top_k, 5)

    def test_baseline_index_action(self):
        """Test baseline indexing action execution."""
        result = self.tool._run(action="index", mode="baseline", repo_paths=[FIXTURE_REPO])
        self.assertIn("Successfully indexed", result)
        self.assertIn("Routes discovered: 2", result)
        self.assertTrue((self.context_dir / "faiss_index").exists())
        self.assertTrue((self.context_dir / "blast_radius_graph.json").exists())

    def test_index_invalid_mode(self):
        result = self.tool._run(action="index", mode="bogus", repo_paths=[FIXTURE_REPO])
        self.assertIn("[ERROR]", result)
        self.assertIn("bogus", result)

    def test_get_inventory_action(self):
        """Test route inventory and technology extraction."""
        result = self.tool._run(action="get_inventory", repo_paths=[FIXTURE_REPO])
        self.assertIn("Route Inventory", result)
        self.assertIn("Technology Inventory", result)
        self.assertIn("flask", result)
        self.assertIn("/login", result)
        self.assertIn("High-Risk Modules", result)

    def test_blast_radius_action(self):
        """Test blast radius calculation action."""
        self.tool._run(action="index", mode="baseline", repo_paths=[FIXTURE_REPO])

        result = self.tool._run(action="get_blast_radius", changed_files=["src/utils/crypto.py"])
        self.assertIn("BLAST RADIUS", result.upper())
        self.assertIn("src/services/auth_service.py", result)

    def test_blast_radius_without_index_errors(self):
        result = self.tool._run(action="get_blast_radius", changed_files=["src/auth.py"])
        self.assertIn("[ERROR]", result)

    def test_semantic_search_action(self):
        """Test semantic code snippet retrieval."""
        self.tool._run(action="index", mode="baseline", repo_paths=[FIXTURE_REPO])

        result = self.tool._run(action="search", query="password hashing", top_k=3)
        self.assertIsNotNone(result)
        self.assertIn("crypto.py", result)

    def test_search_requires_query(self):
        result = self.tool._run(action="search", query=None)
        self.assertIn("[ERROR]", result)

    def test_search_without_index_errors(self):
        result = self.tool._run(action="search", query="anything")
        self.assertIn("[ERROR]", result)

    def test_get_blast_radius_requires_changed_files(self):
        result = self.tool._run(action="get_blast_radius", changed_files=None)
        self.assertIn("[ERROR]", result)

    def test_unknown_action(self):
        result = self.tool._run(action="not_a_real_action")
        self.assertIn("[ERROR]", result)
        self.assertIn("Unknown action", result)

    def test_diff_mode_reembeds_changed_file(self):
        self.tool._run(action="index", mode="baseline", repo_paths=[FIXTURE_REPO])

        crypto_path = Path(FIXTURE_REPO) / "src" / "utils" / "crypto.py"
        original_text = crypto_path.read_text(encoding="utf-8")
        try:
            crypto_path.write_text(
                original_text + "\n\ndef bcrypt_hash(password: str) -> str:\n    return password\n",
                encoding="utf-8",
            )

            result = self.tool._run(
                action="index", mode="diff", repo_paths=[FIXTURE_REPO],
                changed_files=["src/utils/crypto.py"],
            )
            self.assertIn("Successfully refreshed", result)
            self.assertIn("Blast-radius impacted files also refreshed: 3", result)

            search_result = self.tool._run(action="search", query="bcrypt_hash", top_k=3)
            self.assertIn("crypto.py", search_result)
        finally:
            crypto_path.write_text(original_text, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
