import tempfile
import unittest
from pathlib import Path

from app import doc_catalog


class DocCatalogReviewOverridesTest(unittest.TestCase):
    def test_loads_review_overrides_by_doc_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reviews.yaml"
            path.write_text(
                """
reviews:
  - doc_id: 596
    status: framework_auth_only
    reason: 鉴权框架专用。
""".strip(),
                encoding="utf-8",
            )

            self.assertTrue(hasattr(doc_catalog, "load_review_overrides"))
            result = doc_catalog.load_review_overrides(path)

        self.assertEqual(
            result[596],
            {"status": "framework_auth_only", "reason": "鉴权框架专用。"},
        )

    def test_warehouse_terminal_overrides_close_warehouse_review(self):
        reviews = doc_catalog.load_review_overrides("config/api_review_overrides.yaml")
        warehouse_stages = [
            "configured_enabled",
            "configured_enabled",
            "configured_disabled",
            "configured_disabled",
            reviews[1035]["status"],
            reviews[1449]["status"],
        ]
        catalog = [
            {
                "classification": "direct_read_candidate",
                "execution_bucket": "configured" if stage.startswith("configured_") else "terminal_deferred",
                "execution_stage": stage,
                "menu_path": "仓库",
                "configured_enabled": stage == "configured_enabled",
            }
            for stage in warehouse_stages
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(reviews[1035]["status"], "defer_sensitive_credentials")
        self.assertEqual(reviews[1449]["status"], "defer_no_param_source")
        self.assertEqual(
            summary["menu_progress"]["仓库"],
            {
                "total": 6,
                "configured": 4,
                "enabled": 2,
                "terminal_deferred": 2,
                "pending_review": 0,
                "closed": True,
            },
        )

    def test_purchase_relevance_po_info_without_source_is_terminal_deferred(self):
        reviews = doc_catalog.load_review_overrides("config/api_review_overrides.yaml")
        purchase_stages = (
            ["configured_enabled"] * 5
            + ["configured_disabled"]
            + ["defer_write_or_mutation"] * 11
            + [reviews[90]["status"]]
            + ["needs_sensitive_review"] * 4
            + ["known_risk_review"]
        )
        catalog = [
            {
                "classification": "direct_read_candidate",
                "execution_bucket": "configured" if stage.startswith("configured_") else "terminal_deferred",
                "execution_stage": stage,
                "menu_path": "\u91c7\u8d2d",
                "configured_enabled": stage == "configured_enabled",
            }
            for stage in purchase_stages
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(reviews[90]["status"], "defer_no_param_source")
        self.assertEqual(
            summary["menu_progress"]["\u91c7\u8d2d"],
            {
                "total": 23,
                "configured": 6,
                "enabled": 5,
                "terminal_deferred": 12,
                "pending_review": 5,
                "closed": False,
            },
        )

    def test_purchase_plan_detail_without_source_is_terminal_deferred(self):
        reviews = doc_catalog.load_review_overrides("config/api_review_overrides.yaml")
        purchase_stages = (
            ["configured_enabled"] * 5
            + ["configured_disabled"] * 2
            + ["defer_write_or_mutation"] * 11
            + [reviews[90]["status"], reviews[88]["status"]]
            + ["needs_sensitive_review"] * 2
            + ["known_risk_review"]
        )
        catalog = [
            {
                "classification": "direct_read_candidate",
                "execution_bucket": "configured" if stage.startswith("configured_") else "terminal_deferred",
                "execution_stage": stage,
                "menu_path": "\u91c7\u8d2d",
                "configured_enabled": stage == "configured_enabled",
            }
            for stage in purchase_stages
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(reviews[88]["status"], "defer_no_param_source")
        self.assertEqual(
            summary["menu_progress"]["\u91c7\u8d2d"],
            {
                "total": 23,
                "configured": 7,
                "enabled": 5,
                "terminal_deferred": 13,
                "pending_review": 3,
                "closed": False,
            },
        )

    def test_quick_inbound_runtime_rejection_leaves_one_purchase_item_pending(self):
        reviews = doc_catalog.load_review_overrides("config/api_review_overrides.yaml")
        purchase_stages = (
            ["configured_enabled"] * 5
            + ["configured_disabled"] * 3
            + ["defer_write_or_mutation"] * 11
            + [
                reviews[90]["status"],
                reviews[88]["status"],
                reviews[1080]["status"],
            ]
            + ["needs_sensitive_review"]
        )
        catalog = [
            {
                "classification": "direct_read_candidate",
                "execution_bucket": (
                    "configured"
                    if stage.startswith("configured_")
                    else "terminal_deferred"
                ),
                "execution_stage": stage,
                "menu_path": "\u91c7\u8d2d",
                "configured_enabled": stage == "configured_enabled",
            }
            for stage in purchase_stages
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(reviews[1080]["status"], "defer_runtime_rejected")
        self.assertEqual(
            summary["menu_progress"]["\u91c7\u8d2d"],
            {
                "total": 23,
                "configured": 8,
                "enabled": 5,
                "terminal_deferred": 14,
                "pending_review": 1,
                "closed": False,
            },
        )

    def test_purchase_subject_sensitive_override_closes_purchase_review(self):
        reviews = doc_catalog.load_review_overrides("config/api_review_overrides.yaml")
        purchase_stages = (
            ["configured_enabled"] * 5
            + ["configured_disabled"] * 3
            + ["defer_write_or_mutation"] * 11
            + [
                reviews[90]["status"],
                reviews[88]["status"],
                reviews[1080]["status"],
                reviews[5262]["status"],
            ]
        )
        catalog = [
            {
                "classification": "direct_read_candidate",
                "execution_bucket": (
                    "configured"
                    if stage.startswith("configured_")
                    else "terminal_deferred"
                ),
                "execution_stage": stage,
                "menu_path": "\u91c7\u8d2d",
                "configured_enabled": stage == "configured_enabled",
            }
            for stage in purchase_stages
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(
            reviews[5262]["status"],
            "defer_sensitive_credentials",
        )
        self.assertEqual(
            summary["menu_progress"]["\u91c7\u8d2d"],
            {
                "total": 23,
                "configured": 8,
                "enabled": 5,
                "terminal_deferred": 15,
                "pending_review": 0,
                "closed": True,
            },
        )

    def test_inventory_terminal_override_closes_inventory_review(self):
        reviews = doc_catalog.load_review_overrides("config/api_review_overrides.yaml")
        inventory_stages = (
            ["configured_enabled"] * 8
            + ["configured_disabled"]
            + ["defer_write_or_mutation"] * 4
            + [reviews[1022]["status"]]
        )
        catalog = [
            {
                "classification": "direct_read_candidate",
                "execution_bucket": "configured" if stage.startswith("configured_") else "terminal_deferred",
                "execution_stage": stage,
                "menu_path": "库存",
                "configured_enabled": stage == "configured_enabled",
            }
            for stage in inventory_stages
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(reviews[1022]["status"], "defer_runtime_rejected")
        self.assertEqual(
            summary["menu_progress"]["库存"],
            {
                "total": 14,
                "configured": 9,
                "enabled": 8,
                "terminal_deferred": 5,
                "pending_review": 0,
                "closed": True,
            },
        )

    def test_missing_review_config_keeps_backward_compatibility(self):
        self.assertTrue(hasattr(doc_catalog, "load_review_overrides"))

        result = doc_catalog.load_review_overrides("missing-review-config.yaml")

        self.assertEqual(result, {})

    def test_rejects_unknown_review_status(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reviews.yaml"
            path.write_text(
                """
reviews:
  - doc_id: 596
    status: unknown_status
    reason: 虚构测试原因。
""".strip(),
                encoding="utf-8",
            )

            self.assertTrue(hasattr(doc_catalog, "load_review_overrides"))
            with self.assertRaisesRegex(ValueError, "unknown_status"):
                doc_catalog.load_review_overrides(path)

    def test_configured_status_has_priority_over_review_override(self):
        item = {
            "classification": "sensitive_review",
            "configured_api_code": "configured_example",
            "configured_enabled": False,
            "menu_path": "基础数据",
            "api_url": "/middle/base/example/query",
            "api_name": "虚构示例",
        }

        result = doc_catalog.execution_plan_for_api(
            item,
            {"status": "defer_sensitive_credentials", "reason": "虚构测试原因。"},
        )

        self.assertEqual(result["execution_stage"], "configured_disabled")
        self.assertEqual(result["execution_bucket"], "configured")

    def test_review_override_has_priority_over_automatic_classification(self):
        item = {
            "classification": "requires_upstream_params",
            "configured_api_code": "",
            "configured_enabled": False,
            "menu_path": "基础数据",
            "api_url": "/api_token",
            "api_name": "获取令牌",
        }

        result = doc_catalog.execution_plan_for_api(
            item,
            {"status": "framework_auth_only", "reason": "鉴权框架专用。"},
        )

        self.assertEqual(result["execution_stage"], "framework_auth_only")
        self.assertEqual(result["execution_bucket"], "terminal_deferred")
        self.assertEqual(result["execution_reason"], "鉴权框架专用。")

    def test_menu_progress_counts_terminal_and_pending_items(self):
        catalog = [
            self._catalog_item("configured_enabled"),
            self._catalog_item("configured_disabled"),
            self._catalog_item("defer_write_or_mutation"),
            self._catalog_item("framework_auth_only"),
            self._catalog_item("needs_param_source"),
        ]

        summary = doc_catalog._summarize_catalog(catalog, [], {})

        self.assertEqual(
            summary["menu_progress"]["基础数据"],
            {
                "total": 5,
                "configured": 2,
                "enabled": 1,
                "terminal_deferred": 2,
                "pending_review": 1,
                "closed": False,
            },
        )

    @staticmethod
    def _catalog_item(stage):
        bucket = "configured" if stage.startswith("configured_") else "defer_or_review"
        return {
            "classification": "direct_read_candidate",
            "execution_bucket": bucket,
            "execution_stage": stage,
            "menu_path": "基础数据",
            "configured_enabled": stage == "configured_enabled",
        }


if __name__ == "__main__":
    unittest.main()
