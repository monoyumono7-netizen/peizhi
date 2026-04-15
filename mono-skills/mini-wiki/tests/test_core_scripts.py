import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import analyze_project  # noqa: E402
import check_quality  # noqa: E402
import detect_changes  # noqa: E402
import generate_diagram  # noqa: E402
import generate_toc  # noqa: E402
import generate_wiki  # noqa: E402
import init_wiki  # noqa: E402
import plugin_manager  # noqa: E402


def write_web_flow_fixture(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "stage").mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(
        json.dumps(
            {
                "name": "frontend-web-flow",
                "private": True,
                "dependencies": {"react": "^19.0.0"},
                "devDependencies": {"vite": "^7.0.0", "@vitejs/plugin-react": "^5.0.0", "vitest": "^4.0.0"},
            }
        ),
        encoding="utf-8",
    )
    (root / "tsconfig.json").write_text("{}", encoding="utf-8")
    (root / "vite.config.ts").write_text("export default {}", encoding="utf-8")
    (root / "src/main.tsx").write_text("export const boot = () => null;\n", encoding="utf-8")
    (root / "src/app.tsx").write_text("export const App = () => null;\n", encoding="utf-8")

    (root / "src/services").mkdir(parents=True)
    (root / "src/services/index.ts").write_text("export const servicesIndex = () => 1;\n", encoding="utf-8")
    (root / "src/services/request.ts").write_text("export const request = async () => ({ ok: true });\n", encoding="utf-8")
    (root / "src/services/request.test.ts").write_text("export const ignored = true;\n", encoding="utf-8")
    for index in range(7):
        (root / f"src/services/service-{index}.ts").write_text(
            f"export const service{index} = () => {index};\n",
            encoding="utf-8",
        )

    (root / "src/components/chat").mkdir(parents=True)
    (root / "src/components/chat/index.tsx").write_text("export function ChatPanel() { return null; }\n", encoding="utf-8")
    (root / "src/components/chat/use-chat.ts").write_text("export function useChat() { return 1; }\n", encoding="utf-8")
    (root / "src/components/chat/use-chat.test.ts").write_text("export const chatIgnored = true;\n", encoding="utf-8")

    (root / "src/features/workflow").mkdir(parents=True)
    (root / "src/features/workflow/node.ts").write_text("export const workflowNode = () => 1;\n", encoding="utf-8")

    (root / "stage/platform").mkdir(parents=True)
    (root / "stage/index.tsx").write_text("export const StageApp = () => null;\n", encoding="utf-8")
    (root / "stage/platform/main.cc").write_text("int main() { return 0; }\n", encoding="utf-8")
    for index in range(7):
        (root / f"stage/platform/native-{index}.cc").write_text(
            "int main() { return 0; }\n",
            encoding="utf-8",
        )


class AnalyzeProjectTests(unittest.TestCase):
    def test_workspace_react_vite_project_is_detected_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "@acme/root",
                        "private": True,
                        "workspaces": {"packages": ["packages/*", "packages/frontend/*", "packages/common/*"]},
                    }
                ),
                encoding="utf-8",
            )
            (root / "pnpm-workspace.yaml").write_text(
                "packages:\n  - 'packages/**'\n  - '!packages/frontend/web-flow/dist/**'\n",
                encoding="utf-8",
            )
            (root / "turbo.json").write_text("{}", encoding="utf-8")

            api_dir = root / "packages/common/api"
            api_dir.mkdir(parents=True)
            (api_dir / "package.json").write_text(json.dumps({"name": "@acme/api", "version": "1.0.0"}), encoding="utf-8")

            project_dir = root / "packages/frontend/web-flow"
            (project_dir / "src/components/chat").mkdir(parents=True)
            (project_dir / "src/docs").mkdir(parents=True)
            (project_dir / "docs").mkdir(parents=True)
            (project_dir / "stage/platform").mkdir(parents=True)

            (project_dir / "package.json").write_text(
                json.dumps(
                    {
                        "name": "frontend-web-flow",
                        "private": True,
                        "dependencies": {"react": "^19.0.0", "@acme/api": "workspace:*"},
                        "devDependencies": {"vite": "^7.0.0", "@vitejs/plugin-react": "^5.0.0", "vitest": "^4.0.0"},
                    }
                ),
                encoding="utf-8",
            )
            (project_dir / "tsconfig.json").write_text("{}", encoding="utf-8")
            (project_dir / "vite.config.ts").write_text("export default {}", encoding="utf-8")
            (project_dir / "build.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            (project_dir / "README.md").write_text(
                "# React + TypeScript + Vite\n\nThis template provides a minimal setup to get React working in Vite with HMR.\n",
                encoding="utf-8",
            )
            (project_dir / ".mini-wiki").mkdir()
            (project_dir / ".mini-wiki/config.yaml").write_text(
                "exclude:\n  - '*.generated.ts'\n",
                encoding="utf-8",
            )
            (project_dir / "docs/technical-design.md").write_text("# Technical Design\n", encoding="utf-8")
            (project_dir / "src/docs/runtime.md").write_text("# Runtime Notes\n", encoding="utf-8")
            (project_dir / "src/main.tsx").write_text("export const app = 1;\n", encoding="utf-8")
            (project_dir / "src/app.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
            (project_dir / "src/components/chat/index.tsx").write_text("export const Chat = () => null;\n", encoding="utf-8")
            (project_dir / "src/components/chat/use-chat.ts").write_text("export function useChat() {}\n", encoding="utf-8")
            (project_dir / "src/components/chat/use-chat.spec.ts").write_text("export const ignored = true;\n", encoding="utf-8")
            (project_dir / "src/components/chat/generated.generated.ts").write_text("export const ignored = true;\n", encoding="utf-8")
            (project_dir / "stage/platform/main.cc").write_text("int main() { return 0; }\n", encoding="utf-8")

            result = analyze_project.analyze_project(str(project_dir), save_to_cache=False)

            self.assertIn("react", result["project_type"])
            self.assertIn("vite", result["project_type"])
            self.assertIn("monorepo", result["project_type"])
            self.assertIn("cpp", result["project_type"])
            self.assertNotIn("vue", result["project_type"])
            self.assertEqual(
                [{"name": "@acme/api", "path": "packages/common/api", "version": "workspace:*"}],
                result["internal_dependencies"],
            )
            self.assertEqual("design-doc", result["docs_catalog"][0]["kind"])
            self.assertIn("src/docs/runtime.md", result["docs_found"])
            readme_doc = next(doc for doc in result["docs_catalog"] if doc["path"].lower() == "readme.md")
            self.assertEqual("template-readme", readme_doc["kind"])
            components_module = next(module for module in result["modules"] if module["slug"] == "components")
            self.assertEqual(2, components_module["source_files"])

            change_scan = detect_changes.scan_project_files(str(project_dir))
            self.assertNotIn("src/components/chat/generated.generated.ts", change_scan)


class QualityGateTests(unittest.TestCase):
    def test_publish_readiness_requires_approval_even_when_quality_is_ready(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_web_flow_fixture(root)
            init_wiki.init_mini_wiki(temp_dir)
            config_path = root / ".mini-wiki" / "config.yaml"
            config_path.write_text(
                config_path.read_text(encoding="utf-8")
                .replace("review_status_default: approved", "review_status_default: draft")
                .replace("publish_requires_approval: false", "publish_requires_approval: true"),
                encoding="utf-8",
            )

            def fake_quality_gate(wiki_path: str) -> check_quality.QualityReport:
                index_path = Path(wiki_path) / "wiki" / "index.md"
                metrics = check_quality.QualityMetrics(
                    file_path=str(index_path),
                    doc_type="index",
                    quality_level="professional",
                    score_ratio=1.25,
                )
                return check_quality.QualityReport(
                    wiki_path=wiki_path,
                    check_time="2026-04-02T00:00:00Z",
                    total_docs=1,
                    professional_count=1,
                    standard_count=0,
                    basic_count=0,
                    docs=[metrics],
                )

            with mock.patch.object(check_quality, "check_wiki_quality", side_effect=fake_quality_gate):
                result = generate_wiki.generate_wiki(temp_dir, max_module_docs=4, max_api_docs=1)

            self.assertTrue(result["success"])
            self.assertEqual(0, result["summary"]["basic"])

            metadata, _ = check_quality.parse_frontmatter((root / ".mini-wiki/wiki/index.md").read_text(encoding="utf-8"))
            self.assertEqual("draft", metadata["review_status"])
            self.assertEqual("professional", metadata["quality_level"])
            self.assertEqual("1.25", metadata["quality_score"])

    def test_publish_ready_is_false_when_quality_is_blocked_by_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_web_flow_fixture(root)

            def fake_quality_gate(wiki_path: str) -> check_quality.QualityReport:
                index_path = Path(wiki_path) / "wiki" / "index.md"
                metrics = check_quality.QualityMetrics(
                    file_path=str(index_path),
                    doc_type="index",
                    quality_level="professional",
                    score_ratio=1.12,
                    warning_issues=["行数不足: 90/100"],
                )
                return check_quality.QualityReport(
                    wiki_path=wiki_path,
                    check_time="2026-04-02T00:00:00Z",
                    total_docs=1,
                    professional_count=1,
                    standard_count=0,
                    basic_count=0,
                    docs=[metrics],
                )

            with mock.patch.object(check_quality, "check_wiki_quality", side_effect=fake_quality_gate):
                result = generate_wiki.generate_wiki(temp_dir, max_module_docs=4, max_api_docs=1)

            self.assertTrue(result["success"])
            self.assertEqual("needs-improvement", result["summary"]["quality_status"])
            self.assertFalse(result["summary"]["publish_ready"])

    def test_file_protocol_source_link_is_fatal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_path = Path(temp_dir) / "doc.md"
            doc_path.write_text(
                "## 概述\n\n**源码引用**\n[file](file:///tmp/example.ts)\n[相关](./other.md)\n",
                encoding="utf-8",
            )
            metrics = check_quality.analyze_document(
                str(doc_path),
                source_context={"module_type": "module", "source_lines": 20, "source_files": 1, "export_count": 1},
            )
            self.assertEqual("basic", metrics.quality_level)
            self.assertTrue(any("file://" in issue for issue in metrics.fatal_issues))

    def test_dynamic_expectations_prevent_false_professional_rating(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            src_dir = root / "src"
            src_dir.mkdir()
            for index in range(20):
                (src_dir / f"module_{index}.py").write_text(
                    "\n".join([f"def fn_{index}_{item}(): pass" for item in range(20)]),
                    encoding="utf-8",
                )

            wiki_dir = root / ".mini-wiki" / "wiki"
            wiki_dir.mkdir(parents=True)
            doc = wiki_dir / "core.md"
            doc.write_text(
                "---\nsource_paths:\n  - src\nmodule_type: core\n---\n"
                + "\n".join([f"## Section {item}" for item in range(1, 13)])
                + "\n"
                + "\n".join(["```py\npass\n```" for _ in range(5)])
                + "\n```mermaid\nflowchart TB\nA-->B\n```\n"
                + "```mermaid\nclassDiagram\nclass A\n```\n"
                + "**源码引用**\n[src](../src/module_0.py)\n"
                + "[相关](./other.md)\n最佳实践\n性能优化\n错误处理\n"
                + "\n".join(["line" for _ in range(380)]),
                encoding="utf-8",
            )

            report = check_quality.check_wiki_quality(str(root / ".mini-wiki"))
            self.assertEqual(1, report.basic_count)
            self.assertEqual("basic", report.docs[0].quality_level)
            self.assertGreater(report.docs[0].expected_metrics["min_lines"], 1000)

    def test_complete_doc_counts_class_diagram_and_scores_professional(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            doc_path = Path(temp_dir) / "complete.md"
            source_link = "[源码](../src/services/index.ts)"
            sections = [
                "---",
                "source_paths:",
                "  - src/services",
                "module_type: config",
                "---",
                "# Complete Doc",
                "",
                "## Overview",
                "This doc is intentionally complete.",
                "",
                "## Core Model",
                "```mermaid",
                "classDiagram",
                "class ServiceApi",
                "class RequestModel",
                "ServiceApi --> RequestModel",
                "```",
                "",
                "## Flow",
                "```mermaid",
                "flowchart LR",
                'A["Start"] --> B["Finish"]',
                "```",
                "",
                "## Sequence",
                "```mermaid",
                "sequenceDiagram",
                "participant A as Alpha",
                "participant B as Beta",
                "A->>B: Ping",
                "B-->>A: Pong",
                "```",
                "",
                "## Examples",
                "```ts",
                "export const example = 1;",
                "```",
                "",
                "```ts",
                "export const exampleTwo = 2;",
                "```",
                "",
                "## Source",
                source_link,
                "",
                "## Related Docs",
                "[相关文档](./other.md)",
                "",
                "## Appendix",
            ]
            while len(sections) < 210:
                sections.extend([f"Detail line {len(sections)}", ""])
            doc_path.write_text("\n".join(sections), encoding="utf-8")

            metrics = check_quality.analyze_document(
                str(doc_path),
                source_context={"module_type": "config", "source_lines": 200, "source_files": 10, "export_count": 4},
            )

            self.assertEqual(1, metrics.class_diagram_count)
            self.assertEqual("professional", metrics.quality_level)
            self.assertGreaterEqual(metrics.score_ratio, 1.2)
            self.assertFalse(metrics.fatal_issues)
            self.assertFalse(metrics.warning_issues)

    def test_index_doc_with_zero_expected_examples_is_not_penalized(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wiki_dir = Path(temp_dir) / ".mini-wiki" / "wiki"
            wiki_dir.mkdir(parents=True)
            doc_path = wiki_dir / "doc-map.md"
            lines = [
                "# 阅读地图",
                "",
                "## 推荐阅读顺序",
                "```mermaid",
                "flowchart LR",
                'A["首页"] --> B["架构"]',
                "```",
                "",
                "## 自动生成文档索引",
                "| 文档 | 类型 |",
                "|------|------|",
                "| [架构](./architecture.md) | 自动生成 |",
                "",
                "## 领域优先级",
                "内容说明",
                "",
                "## 原始设计资产映射",
                "内容说明",
                "",
                "## 文档治理契约",
                "内容说明",
                "",
                "## 使用建议",
                "内容说明",
                "",
                "## 相关文档",
                "- [架构](./architecture.md)",
            ]
            while len(lines) < 92:
                lines.append(f"补充说明 {len(lines)}")
            doc_path.write_text("\n".join(lines), encoding="utf-8")

            metrics = check_quality.analyze_document(
                str(doc_path),
                source_context={"module_type": "project", "doc_profile": "topic", "doc_role": "project"},
            )

            self.assertEqual("professional", metrics.quality_level)
            self.assertFalse(metrics.warning_issues)

    def test_design_doc_summary_skips_agent_chatter(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            doc_path = root / "cloud-agent-sdk-events.md"
            doc_path.write_text(
                "\n".join(
                    [
                        "我来帮你分析 `ActiveSessionImpl` 和 `CloudAgentConnection` 的事件系统区别。让我先查看相关代码。",
                        "现在让我再查看一下 `SessionEvents` 和 `ClientEvents` 的具体定义，以便全面比较两者的事件系统：",
                        "",
                        "---",
                        "",
                        "ActiveSessionImpl 是面向调用方的会话层抽象，它包装了 CloudAgentConnection 并屏蔽了底层连接事件。",
                    ]
                ),
                encoding="utf-8",
            )

            summary = generate_wiki.extract_doc_summary(root, "cloud-agent-sdk-events.md")

            self.assertIn("ActiveSessionImpl 是面向调用方的会话层抽象", summary)
            self.assertNotIn("我来帮你分析", summary)

    def test_render_class_diagram_uses_real_references_only(self) -> None:
        empty_diagram = generate_wiki.render_exports_class_diagram(
            [
                {
                    "name": "toolCallRendererRegistry",
                    "type": "re-export",
                    "signature": "export { toolCallRendererRegistry } from './registry';",
                }
            ]
        )
        self.assertEqual("", empty_diagram)

        typed_diagram = generate_wiki.render_exports_class_diagram(
            [
                {
                    "name": "RequestQueryParams",
                    "type": "interface",
                    "signature": "export interface RequestQueryParams {",
                },
                {
                    "name": "HttpRequestOptions",
                    "type": "type",
                    "signature": "export type HttpRequestOptions = Omit<RequestInit, 'body'> & {",
                },
                {
                    "name": "ResponseError",
                    "type": "type",
                    "signature": "export type ResponseError = {",
                },
            ]
        )

        self.assertIn("classDiagram", typed_diagram)
        self.assertNotIn("ApiSurface", typed_diagram)
        self.assertNotIn("RequestQueryParams --> HttpRequestOptions", typed_diagram)

    def test_generation_signature_change_disables_incremental_skip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "OWNERS").write_text("alice\n", encoding="utf-8")
            write_web_flow_fixture(root)

            def fake_quality_gate(wiki_path: str) -> check_quality.QualityReport:
                index_path = Path(wiki_path) / "wiki" / "index.md"
                metrics = check_quality.QualityMetrics(
                    file_path=str(index_path),
                    doc_type="index",
                    quality_level="professional",
                    score_ratio=1.25,
                )
                return check_quality.QualityReport(
                    wiki_path=wiki_path,
                    check_time="2026-04-02T00:00:00Z",
                    total_docs=1,
                    professional_count=1,
                    standard_count=0,
                    basic_count=0,
                    docs=[metrics],
                )

            with mock.patch.object(check_quality, "check_wiki_quality", side_effect=fake_quality_gate):
                first = generate_wiki.generate_wiki(temp_dir, max_module_docs=3, max_api_docs=1)

            self.assertTrue(first["success"])
            self.assertFalse(first.get("skipped", False))

            meta_path = root / ".mini-wiki" / "meta.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["generation_signature"] = "stale-signature"
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

            with mock.patch.object(check_quality, "check_wiki_quality", side_effect=fake_quality_gate):
                second = generate_wiki.generate_wiki(temp_dir, max_module_docs=3, max_api_docs=1)

            self.assertFalse(second.get("skipped", False))

    def test_prepare_progress_state_resumes_pending_modules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            progress_file = root / ".mini-wiki" / "cache" / "progress.json"
            progress_file.parent.mkdir(parents=True, exist_ok=True)

            settings = {
                "progressive_mode": "always",
                "progressive_batch_size": 2,
                "progressive_resume_from_cache": True,
            }
            analysis = {"stats": {"total_files": 120, "source_lines": 12000}}
            selected_modules = [{"slug": "workflow"}, {"slug": "chat"}, {"slug": "services"}]
            api_modules = [{"slug": "services"}, {"slug": "events"}]
            signature = "resume-test-signature"
            progress_file.write_text(
                json.dumps(
                    {
                        "version": generate_wiki.GENERATOR_VERSION,
                        "quality_ruleset_version": generate_wiki.QUALITY_RULESET_VERSION,
                        "generation_signature": signature,
                        "completed_modules": ["workflow"],
                        "completed_api_modules": ["events"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            progress_path, progress_state, pending_modules, pending_api_modules = generate_wiki.prepare_progress_state(
                root,
                settings,
                analysis,
                selected_modules,
                api_modules,
                signature,
                force_full=False,
            )

            self.assertEqual(progress_file, progress_path)
            self.assertEqual(["workflow"], progress_state["completed_modules"])
            self.assertEqual(["events"], progress_state["completed_api_modules"])
            self.assertEqual(["chat", "services"], [module["slug"] for module in pending_modules])
            self.assertEqual(["services"], [module["slug"] for module in pending_api_modules])
            self.assertEqual(3, progress_state["total_modules"])
            self.assertEqual(2, progress_state["total_api_modules"])

    def test_generation_signature_changes_when_publish_contract_changes(self) -> None:
        settings_a = {
            "profile_name": "web-flow",
            "doc_profile": "overview",
            "language": "zh",
            "review_status": "draft",
            "publish_requires_approval": True,
            "source_link_style": "relative",
            "minimum_publish_quality": "professional",
            "block_publish_on_warnings": True,
        }
        settings_b = dict(settings_a)
        settings_b["review_status"] = "approved"
        settings_b["publish_requires_approval"] = False

        signature_a = generate_wiki.build_generation_signature(settings_a, {}, [])
        signature_b = generate_wiki.build_generation_signature(settings_b, {}, [])

        self.assertNotEqual(signature_a, signature_b)

    def test_web_flow_profile_fixture_prefers_actual_context_over_focus_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write_web_flow_fixture(root)

            analysis = analyze_project.analyze_project(str(root), save_to_cache=False)
            selected_modules = generate_wiki.choose_focus_modules(analysis["modules"], 4)

            self.assertEqual(["stage", "services"], [module["slug"] for module in selected_modules])

            stage_module = next(module for module in selected_modules if module["slug"] == "stage")
            services_module = next(module for module in selected_modules if module["slug"] == "services")

            api_modules = generate_wiki.select_api_modules(selected_modules, 2)
            self.assertEqual(["services"], [module["slug"] for module in api_modules])

            stage_focus = generate_wiki.choose_focus_files(root, stage_module, 3)
            service_focus = generate_wiki.choose_focus_files(root, services_module, 3)

            self.assertEqual("stage/index.tsx", stage_focus[0])
            self.assertEqual("src/services/index.ts", service_focus[0])
            self.assertNotIn("src/services/request.test.ts", service_focus)
            self.assertNotIn("src/components/chat/use-chat.test.ts", service_focus)

            actual_context_score = generate_wiki.score_focus_file(
                root / "src/services/index.ts",
                root,
                services_module["slug"],
            )
            focus_context_score = generate_wiki.score_focus_file(
                root / "src/services/request.test.ts",
                root,
                services_module["slug"],
            )
            self.assertGreater(actual_context_score, focus_context_score)


class DiagramAndInitTests(unittest.TestCase):
    def test_architecture_diagram_has_no_missing_frontend_node(self) -> None:
        diagram = generate_diagram.generate_architecture_diagram({"modules": [], "project_type": ["python"]})
        self.assertNotIn("Frontend -->", diagram)
        self.assertIn('App["应用"]', diagram)

    def test_init_wiki_creates_new_schema_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = init_wiki.init_mini_wiki(temp_dir)
            self.assertTrue(result["success"])
            config = (Path(temp_dir) / ".mini-wiki/config.yaml").read_text(encoding="utf-8")
            structure = json.loads((Path(temp_dir) / ".mini-wiki/cache/structure.json").read_text(encoding="utf-8"))
            self.assertIn("progressive:", config)
            self.assertIn("governance:", config)
            self.assertIn("review_status_default: approved", config)
            self.assertIn("publish_requires_approval: false", config)
            self.assertIn("minimum_publish_quality: professional", config)
            self.assertIn("workspace_root", structure)
            self.assertIn("docs_catalog", structure)

    def test_load_generation_settings_defaults_to_direct_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = generate_wiki.load_generation_settings(Path(temp_dir))

            self.assertEqual("approved", settings["review_status"])
            self.assertFalse(settings["publish_requires_approval"])
            self.assertEqual("professional", settings["minimum_publish_quality"])
            self.assertTrue(settings["block_publish_on_warnings"])

    def test_prune_stale_generated_docs_keeps_manual_docs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            wiki_dir = Path(temp_dir) / "wiki"
            wiki_dir.mkdir(parents=True)
            kept = wiki_dir / "index.md"
            stale = wiki_dir / "old-domain.md"
            manual = wiki_dir / "manual-note.md"

            kept.write_text(
                "---\ngenerated_by: mini-wiki-generator\n---\n# Index\n",
                encoding="utf-8",
            )
            stale.write_text(
                "---\ngenerated_by: mini-wiki-generator\n---\n# Old\n",
                encoding="utf-8",
            )
            manual.write_text("# Manual\n", encoding="utf-8")

            removed = generate_wiki.prune_stale_generated_docs(wiki_dir, [kept])

            self.assertEqual([str(stale)], removed)
            self.assertTrue(kept.exists())
            self.assertFalse(stale.exists())
            self.assertTrue(manual.exists())

    def test_generate_wiki_produces_governed_docs_and_quality_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "OWNERS").write_text("alice\nbob\n", encoding="utf-8")
            (root / "docs").mkdir()
            (root / "docs/technical-design.md").write_text("# Technical Design\n\nWorkflow overview.\n", encoding="utf-8")
            (root / "stage/platform").mkdir(parents=True)
            (root / "src/components/chat").mkdir(parents=True)
            (root / "src/components/workflow").mkdir(parents=True)
            (root / "src/services").mkdir(parents=True)
            (root / "src/events").mkdir(parents=True)

            (root / "package.json").write_text(
                json.dumps(
                    {
                        "name": "frontend-web-flow",
                        "private": True,
                        "dependencies": {"react": "^19.0.0"},
                        "devDependencies": {"vite": "^7.0.0", "@vitejs/plugin-react": "^5.0.0", "vitest": "^4.0.0"},
                        "scripts": {"dev": "vite", "build": "vite build", "test": "vitest run"},
                    }
                ),
                encoding="utf-8",
            )
            (root / "tsconfig.json").write_text("{}", encoding="utf-8")
            (root / "vite.config.ts").write_text("export default {}", encoding="utf-8")
            (root / "src/main.tsx").write_text("export const boot = () => null;\n", encoding="utf-8")
            (root / "src/app.tsx").write_text("export const App = () => null;\n", encoding="utf-8")
            (root / "src/components/chat/index.tsx").write_text(
                "export function ChatPanel() { return null; }\nexport const useChatView = () => null;\n",
                encoding="utf-8",
            )
            (root / "src/components/chat/render.tsx").write_text(
                "export function renderChat() { return null; }\n",
                encoding="utf-8",
            )
            for index in range(7):
                (root / f"src/components/chat/tool-{index}.ts").write_text(
                    f"export const chatTool{index} = () => {index};\n",
                    encoding="utf-8",
                )
            (root / "src/components/workflow/index.tsx").write_text(
                "export function WorkflowCanvas() { return null; }\n",
                encoding="utf-8",
            )
            (root / "src/components/workflow/store.ts").write_text(
                "export const useWorkflowStore = () => null;\n",
                encoding="utf-8",
            )
            for index in range(7):
                (root / f"src/components/workflow/node-{index}.ts").write_text(
                    f"export const workflowNode{index} = () => {index};\n",
                    encoding="utf-8",
                )
            (root / "src/services/fetch.ts").write_text(
                "export const request = async () => ({ ok: true });\nexport const getBaseUrl = () => '/api';\n",
                encoding="utf-8",
            )
            for index in range(5):
                (root / f"src/services/service-{index}.ts").write_text(
                    f"export const service{index} = async () => {index};\n",
                    encoding="utf-8",
                )
            (root / "src/events/index.ts").write_text("export const emit = () => undefined;\n", encoding="utf-8")
            for index in range(5):
                (root / f"src/events/event-{index}.ts").write_text(
                    f"export const event{index} = () => 'event-{index}';\n",
                    encoding="utf-8",
                )
            (root / "stage/index.tsx").write_text("export const StageApp = () => null;\n", encoding="utf-8")
            (root / "stage/platform/main.cc").write_text("int main() { return 0; }\n", encoding="utf-8")
            for index in range(7):
                (root / f"stage/shared-{index}.ts").write_text(
                    f"export const stagePart{index} = () => {index};\n",
                    encoding="utf-8",
                )

            result = generate_wiki.generate_wiki(temp_dir, max_module_docs=4, max_api_docs=1)

            self.assertGreaterEqual(result["summary"]["professional"], 2)
            self.assertLessEqual(result["summary"]["basic"], 2)
            self.assertGreaterEqual(len(result["generated_files"]), 5)

            index_doc = (root / ".mini-wiki/wiki/index.md").read_text(encoding="utf-8")
            self.assertIn("owner: alice", index_doc)
            self.assertIn("source_paths:", index_doc)

            report_path = root / ".mini-wiki/quality-report.json"
            self.assertTrue(report_path.exists())

            toc = generate_toc.generate_toc(str(root / ".mini-wiki/wiki"))
            self.assertIn("领域文档", toc)
            if any("/api/" in path for path in result["generated_files"]):
                self.assertIn("API 文档", toc)


class PluginManagerTests(unittest.TestCase):
    def _write_plugin_archive(self, archive_path: Path) -> None:
        plugin_dir = archive_path.parent / "plugin-src"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "PLUGIN.md").write_text(
            "---\nname: sample-plugin\ntype: enhancer\nversion: 1.2.3\n---\n\n# Sample Plugin\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.write(plugin_dir / "PLUGIN.md", arcname="sample-plugin-main/PLUGIN.md")

    def test_remote_plugin_install_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = plugin_manager.install_plugin(temp_dir, "owner/repo")
            self.assertFalse(result["success"])
            self.assertIn("Remote plugin install is disabled", result["message"])

    def test_remote_plugin_install_preserves_source_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            archive_path = Path(temp_dir) / "sample.zip"
            self._write_plugin_archive(archive_path)

            def fake_download(project_root: str, metadata: dict, destination: Path) -> None:
                destination.write_bytes(archive_path.read_bytes())

            with mock.patch.dict(os.environ, {"MINI_WIKI_ALLOW_REMOTE_INSTALL": "1"}):
                with mock.patch.object(plugin_manager, "download_remote_archive", side_effect=fake_download):
                    result = plugin_manager.install_plugin(temp_dir, "owner/repo")

            self.assertTrue(result["success"])
            registry = plugin_manager.load_registry(temp_dir)
            entry = registry["plugins"][0]
            self.assertEqual("github", entry["source"]["type"])
            self.assertEqual("owner/repo", entry["source"]["origin"])


if __name__ == "__main__":
    unittest.main()
