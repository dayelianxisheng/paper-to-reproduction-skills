from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_vln_note.py"
SPEC = importlib.util.spec_from_file_location("audit_vln_note", SCRIPT)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


VALID_WORKING_ANALYSIS = """
# Working analysis

- 主创新层：Inference & planning
- 支撑创新层：Representation & memory
- AUTHOR：论文从最近的前序范式 DUET 出发，改变在线节点生成方式。
- 最强受控消融证据：Table 3 的 SR 从 31% 变为 36%，支持该机制有效。
- 公式分类：新的图距离 bias 为 MUST-DERIVE；标准交叉熵为 SKIP。
- 训练：使用导航图投影作为监督。
- 推理：只使用 RGB-D 和在线状态。
- 依赖、成本与边界：依赖深度和位姿，增加图内存与规划延迟。
- Demo suitability: HIGH。

## 一句话历史位置

该方法把离散图上的全局选择扩展到连续环境中的在线拓扑规划。
"""


class AuditVlnNoteTests(unittest.TestCase):
    def test_valid_working_analysis_passes(self) -> None:
        findings = audit.audit_working_analysis(
            VALID_WORKING_ANALYSIS, "page-grounded"
        )
        self.assertFalse(
            [item for item in findings if item["severity"] == "error"], findings
        )

    def test_structure_grounded_rejects_page_anchor(self) -> None:
        findings = audit.audit_working_analysis(
            VALID_WORKING_ANALYSIS + "\n见 p. 7。", "structure-grounded"
        )
        codes = {item["code"] for item in findings}
        self.assertIn("unsafe-page-anchor", codes)

    def test_structure_grounded_allows_visually_verified_page_anchor(self) -> None:
        findings = audit.audit_working_analysis(
            VALID_WORKING_ANALYSIS + "\n见 p. 7。",
            "structure-grounded",
            verified_page_anchors=True,
        )
        codes = {item["code"] for item in findings}
        self.assertNotIn("unsafe-page-anchor", codes)

    def test_source_limited_rejects_unseen_table(self) -> None:
        findings = audit.audit_working_analysis(
            VALID_WORKING_ANALYSIS, "source-limited"
        )
        codes = {item["code"] for item in findings}
        self.assertIn("unseen-structural-anchor", codes)

    def test_path_note_does_not_require_full_working_record(self) -> None:
        text = """
# 路径一

## 第一篇：示例

### 创新定位

主创新是在线拓扑。

### 一句话历史位置

它把局部候选提升为可回退的全局记忆。
"""
        findings = audit.audit_path_note(text, None)
        self.assertFalse(
            [item for item in findings if item["severity"] == "error"], findings
        )

    def test_path_note_rejects_placeholder(self) -> None:
        findings = audit.audit_path_note("# 路径\n\nTODO：以后再写。\n", None)
        self.assertIn("placeholder-content", {item["code"] for item in findings})


if __name__ == "__main__":
    unittest.main()
