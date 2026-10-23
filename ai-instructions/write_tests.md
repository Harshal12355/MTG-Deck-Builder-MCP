# Writing Tests

## Quick Reference

Before writing any test:
1. Find an existing test file in the same area as reference (`webatds/tests/` mirrors `webatds/`).
2. Identify the base test class to use (`CustomTestCase` or `CustomAPITestCase` from `webatds.tests.custom_test_cases`).
3. Follow the rules below strictly.

### Core Rules

| Rule | Do | Don't |
|------|-----|-------|
| Test behavior | Test outcomes (state changes, return values, responses) | Test implementation details (private methods, internal call order) |
| Don't test Django | Test custom business logic, domain rules, permissions, queries | Test ORM `.create()`, ForeignKey cascade, standard DRF/field types |
| Setup method | Use `@classmethod setUpTestData(cls)` for shared read-only DB rows | Put DB row creation in `setUp(self)` (runs before every test) |
| URLs in API tests | Use `reverse("endpoint_name")` (singular, per `conventions.md`) | Hardcode `"/api/..."` paths |
| Mock scope | Mock external boundaries (APIs, BAML `b.*`, third-party services) | Mock internal methods of the service under test |
| Assertions | Use specific assertions (`assertEqual`, `assertIsNone`, `assertAlmostEqual`) | Use generic `assertTrue(x == y)` or `assertFalse(x)` |
| Independence | Create mutable test objects inside each test (or reset via `refresh_from_db()`) | Mutate shared `cls.*` objects across tests without refreshing |
| Docstrings | Use self-explanatory `test_<behavior>` names (docstrings optional, max 1 line) | Write multi-line docstrings restating the test name |

---

## Templates

### Model / Service Test Template

```python
from webatds.tests import utils
from webatds.tests.custom_test_cases import CustomTestCase


class InvoiceCreationServiceTests(CustomTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(
            name="Test Company",
            contact_email="test@company.com",
            ai_ingest_email="ai@test.com",
        )
        cls.user = cls.company.employees.first()

    @classmethod
    def _create_invoice(cls, **overrides):
        defaults = {"creator_company": cls.company, "invoice_number": "INV-001"}
        defaults.update(overrides)
        return Invoice.objects.create(**defaults)

    def test_duplicate_invoice_links_to_original(self):
        original = self._create_invoice(invoice_number="INV-001")
        duplicate = self._create_invoice(invoice_number="INV-001")

        duplicate.mark_as_duplicate(original, confidence=0.95)

        duplicate.refresh_from_db()
        self.assertTrue(duplicate.is_duplicate)
        self.assertFalse(duplicate.is_current)
        self.assertEqual(duplicate.duplicate_of, original)
        self.assertAlmostEqual(duplicate.duplicate_confidence, 0.95, places=6)
```

### API Test Template (`setUpTestData` + minimal `setUp`)

Keep DB creation in `setUpTestData` and use `setUp` only for per-test client state like `force_login`:

```python
from django.urls import reverse
from rest_framework import status

from webatds.tests import utils
from webatds.tests.custom_test_cases import CustomAPITestCase


class OutboundInvoiceTests(CustomAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.company = utils.create_company(
            name="Test Company",
            contact_email="test@company.com",
            ai_ingest_email="ai@test.com",
        )
        cls.user = cls.company.employees.first()
        cls.invoice = cls._create_invoice()
        cls.url = reverse("outbound_invoice")

    def setUp(self):
        self.client.force_login(self.user)

    @classmethod
    def _create_invoice(cls, **overrides):
        defaults = {"creator_company": cls.company, "currency": "USD"}
        defaults.update(overrides)
        return Invoice.objects.create(**defaults)

    def test_list_returns_only_company_invoices(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for invoice in response.data:
            self.assertEqual(invoice["company"], self.company.id)
```

---

## Key Patterns

### 1. Parameterized Edge Cases with `subTest`

Avoid writing separate test methods that only vary input data. Group boundary cases (empty, `None`, zero, malformed, large values) with `subTest`:

```python
def test_parse_currency_and_amount(self):
    cases = [
        ("$20.00", Currency.USD, Decimal("20.00")),
        ("€15.50", Currency.EUR, Decimal("15.50")),
        ("$0.00", Currency.USD, Decimal("0.00")),
        ("$1,234,567.89", Currency.USD, Decimal("1234567.89")),
    ]
    for raw, expected_currency, expected_amount in cases:
        with self.subTest(raw=raw):
            currency, amount = parse_currency_and_amount(raw)
            self.assertEqual(currency, expected_currency)
            self.assertEqual(amount, expected_amount)

def test_parse_currency_invalid_inputs_return_none(self):
    for invalid in ["invalid", "", None, "abc$def", "$$20.00"]:
        with self.subTest(invalid=invalid):
            currency, amount = parse_currency_and_amount(invalid)
            self.assertIsNone(currency)
            self.assertIsNone(amount)
```

### 2. Mocking External Boundaries

Mock at the system edge (external HTTP, BAML `b.<FunctionName>`), verify the call arguments, and assert the resulting domain state:

```python
@patch("webatds.inbound_email.services.b.GetVendorFromName")
def test_vendor_matching_uses_llm_result(self, mock_get_vendor):
    vendor = models.Vendor.objects.create(name="Acme Corp", company=self.company)
    mock_get_vendor.return_value = "Acme Corp"

    invoice = InvoiceCreationService.create_matched_invoice_data(self.invoice_data.id)

    mock_get_vendor.assert_called_once()
    self.assertEqual(invoice.vendor, vendor)
```

Note: When asserting exact arguments on a mocked BAML function called via `call_llm`, expect the injected collector (`baml_options={"collector": ANY}`).

### 3. Transaction Rollback & Error Conditions

Verify both the raised exception and that partial writes rolled back:

```python
def test_transaction_rollback_on_duplicate_detection_failure(self):
    invoice_data = self._create_inbound_invoice_data("INV-ROLLBACK")
    initial_count = Invoice.objects.count()

    with patch(
        "webatds.invoicing.services.creation.InvoiceDuplicateDetector.detect_duplicates",
        side_effect=RuntimeError("Duplicate detection failed!"),
    ):
        with self.assertRaises(RuntimeError):
            InvoiceCreationService.create_matched_invoice_data(invoice_data.id)

    self.assertEqual(Invoice.objects.count(), initial_count)
```

### 4. Batch Test Data Creation

Use `bulk_create` when a test needs many rows instead of calling `.create()` in a loop:

```python
Invoice.objects.bulk_create([
    Invoice(creator_company=self.company, invoice_number=f"INV-{i}") for i in range(10)
])
```

---

## Running Tests

Prefer `--keepdb` when running iteratively; omit `--keepdb` after migration or schema changes:

```bash
# Specific test file
python manage.py test webatds.tests.module.test_file --keepdb

# Specific test class or method
python manage.py test webatds.tests.module.test_file.TestClassName.test_method --keepdb
```

### File Placement

Tests live under `webatds/tests/` mirroring the source module path:

```
webatds/invoicing/services/creation.py
  -> webatds/tests/invoicing/services/test_creation.py
```
