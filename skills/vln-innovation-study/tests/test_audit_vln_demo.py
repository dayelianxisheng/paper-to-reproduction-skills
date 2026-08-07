from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_vln_demo.py"
SPEC = importlib.util.spec_from_file_location("audit_vln_demo", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


README = """
# 示例

这是一个 **Mechanism Demo**。

## 因果对照

基线表现出局部贪心失败；控制变量保持相同，只改变是否保存拓扑历史。

## 运行

```bash
python main.py --seed 7
```

## 这个 Demo 证明什么

结果支持在线拓扑可以解决构造的回退失败。

## 它不证明什么

不证明真实 VLN benchmark 性能，也不是论文复现。
"""


class AuditVlnDemoTests(unittest.TestCase):
    def build_demo(self, root: Path, readme: str = README) -> Path:
        demo = root / "demo"
        outputs = demo / "outputs"
        outputs.mkdir(parents=True)
        (demo / "README.md").write_text(readme, encoding="utf-8")
        (demo / "main.py").write_text(
            "seed = 7\nprint('中文图表')\n", encoding="utf-8"
        )
        (outputs / "figure.png").write_bytes(b"png")
        (outputs / "metrics.json").write_text('{"success": 1.0}\n', encoding="utf-8")
        return demo

    def test_complete_demo_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            report = audit.audit_demo(self.build_demo(Path(directory)))
            self.assertTrue(report["passed"], report)

    def test_missing_non_claim_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            readme = README.replace("## 它不证明什么\n\n不证明真实 VLN benchmark 性能，也不是论文复现。\n", "")
            report = audit.audit_demo(self.build_demo(Path(directory), readme))
            codes = {item["code"] for item in report["findings"]}
            self.assertIn("missing-non-claim", codes)


if __name__ == "__main__":
    unittest.main()
