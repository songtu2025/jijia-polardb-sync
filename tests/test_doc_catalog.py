import unittest

from app.doc_catalog import classify_api_detail


class DocCatalogClassificationTest(unittest.TestCase):
    def test_classifies_page_api_without_business_required_fields_as_direct_candidate(self):
        detail = {
            "apiUrl": "/purchase/goods/brand/page",
            "erpMethod": "Post",
            "opType": "page",
            "requestBody": [
                {"name": "page", "must": True, "children": []},
                {"name": "pagesize", "must": True, "children": []},
                {"name": "name", "must": False, "children": []},
            ],
            "responseBody": [
                {
                    "name": "data",
                    "type": "object",
                    "children": [
                        {"name": "rows", "type": "array<object>", "children": []},
                        {"name": "total", "type": "int", "children": []},
                    ],
                }
            ],
        }

        result = classify_api_detail(detail)

        self.assertEqual(result["classification"], "direct_read_candidate")
        self.assertEqual(result["business_required_fields"], [])
        self.assertIs(result["has_page_response"], True)

    def test_classifies_query_api_with_business_required_fields_as_dependency(self):
        detail = {
            "apiUrl": "/middle/base/warehouseIds/query",
            "erpMethod": "Get",
            "opType": "query",
            "requestBody": [
                {"name": "marketIdList", "must": True, "children": []},
            ],
            "responseBody": [
                {"name": "data", "type": "array<object>", "children": []},
            ],
        }

        result = classify_api_detail(detail)

        self.assertEqual(result["classification"], "requires_upstream_params")
        self.assertEqual(result["business_required_fields"], ["marketIdList"])

    def test_classifies_response_with_sensitive_fields_for_review(self):
        detail = {
            "apiUrl": "/middle/base/allUser/list",
            "erpMethod": "Get",
            "opType": "list",
            "requestBody": [],
            "responseBody": [
                {
                    "name": "data",
                    "type": "array<object>",
                    "children": [
                        {"name": "email", "type": "string", "description": "邮箱", "children": []},
                    ],
                }
            ],
        }

        result = classify_api_detail(detail)

        self.assertEqual(result["classification"], "sensitive_review")
        self.assertIs(result["has_sensitive_response_fields"], True)

    def test_classifies_mutation_api_as_write_or_mutation(self):
        detail = {
            "apiUrl": "/middle/base/rate/update",
            "erpMethod": "Post",
            "opType": "update",
            "requestBody": [
                {"name": "currency", "must": True, "children": []},
            ],
            "responseBody": [
                {"name": "data", "type": "object", "children": []},
            ],
        }

        result = classify_api_detail(detail)

        self.assertEqual(result["classification"], "write_or_mutation")
