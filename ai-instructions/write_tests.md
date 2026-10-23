# Writing Tests

## Quick Reference

When writing tests, follow these rules strictly.

### Pre-Flight Checklist

Before writing any test:
1. Find an existing test file in the same area as reference
2. Identify the base test class to use (`CustomTestCase` or `CustomAPITestCase`)
3. Review the detailed guidelines below for specific patterns

### Core Rules

| Rule | Do | Don't |
|------|-----|-------|
| Test behavior | Test what code does (outcomes) | Test how code works (implementation) |
| Setup method | Use `@classmethod setUpTestData(cls)` | Use `setUp(self)` |
| Mock scope | Mock external services (APIs, LLMs) | Mock internal business logic |
| Assertions | Use specific assertions (`assertEqual`, `assertIsNone`) | Use generic `assertTrue(x == y)` |
| Independence | Each test creates its own mutable data | Tests share or depend on each other |

### Test Structure Template

```python
from webatds.tests.custom_test_cases import CustomTestCase
from webatds.tests import utils


class YourFeatureTests(CustomTestCase):
    """Test description."""

    @classmethod
    def setUpTestData(cls):
        """Set up immutable test data once for all tests."""
        cls.company = utils.create_company(
            name="Test Company",
            contact_email="test@company.com",
            ai_ingest_email="ai@test.com",
        )
        cls.user = cls.company.employees.first()

    def _create_test_object(self, **overrides):
        """Helper to create test objects with defaults."""
        defaults = {
            "company": self.company,
            # ... other defaults
        }
        defaults.update(overrides)
        return YourModel.objects.create(**defaults)

    def test_feature_does_expected_thing(self):
        # ARRANGE
        obj = self._create_test_object()

        # ACT
        result = obj.some_method()

        # ASSERT
        self.assertEqual(result, expected_value)
```

### API Test Template

```python
from webatds.tests.custom_test_cases import CustomAPITestCase
from rest_framework import status


class YourEndpointTests(CustomAPITestCase):
    """Test API endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)
        cls.user = cls.company.employees.first()

    def test_endpoint_returns_expected_data(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get("/api/your-endpoint/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["field"], expected_value)
```

### Running Tests

```bash
# Specific test file
python manage.py test webatds.tests.module.test_file

# Specific test class
python manage.py test webatds.tests.module.test_file.TestClassName

# Specific test method
python manage.py test webatds.tests.module.test_file.TestClassName.test_method
```

When running backend Django tests iteratively, prefer adding `--keepdb` when the test database already exists:

```bash
python manage.py test webatds.tests.module.test_file --keepdb
```

Omit `--keepdb` when validating migrations, changing schema, debugging test database setup, or if the test database appears stale.

### File Placement

Tests go in `webatds/tests/` mirroring the source structure:

```
webatds/
├── invoicing/
│   └── services/
│       └── creation.py
└── tests/
    └── invoicing/
        └── services/
            └── test_creation.py
```

---

# Detailed Testing Guidelines

## Overview

This document describes the testing patterns, conventions, and best practices used in the ATDS project. Following these patterns ensures consistency, maintainability, and reliability across our test suite.

**Test Location:** `/workspace/backend/atds/webatds/tests/`

---

## Core Principles

### Test Behavior, Not Implementation

**DO:** Test what the code does (behavior), not how it does it (implementation)

```python
# ✅ GOOD - Tests behavior
def test_invoice_marked_as_duplicate_when_same_invoice_number_and_date(self):
    """Test that invoices with same number and date are marked as duplicates."""
    original = self._create_test_invoice("INV-001", date)
    duplicate = self._create_test_invoice("INV-001", date)

    duplicate.refresh_from_db()
    self.assertTrue(duplicate.is_duplicate)
    self.assertEqual(duplicate.duplicate_of, original)


# ❌ BAD - Tests implementation details
def test_duplicate_detection_calls_calculate_confidence(self):
    """Test that detect_duplicates calls _calculate_confidence."""
    # Don't test that internal methods are called
    # Test the outcome instead
```

**Why:** Implementation can change, but behavior should remain consistent. Testing behavior makes tests more resilient to refactoring.

**More Examples:**

```python
# ❌ BAD - Testing implementation (how)
def test_invoice_creation_calls_vendor_matching_service(self):
    """Test that create_matched_invoice_data calls VendorMatchingService."""
    with patch("webatds.invoicing.services.creation.VendorMatchingService") as mock_service:
        InvoiceCreationService.create_matched_invoice_data(invoice_id)
        mock_service.find_vendor_match.assert_called()
    # This tests HOW it works, not WHAT it does


# ✅ GOOD - Testing behavior (what)
def test_invoice_creation_matches_vendor_to_invoice(self):
    """Test that invoice creation assigns the correct vendor."""
    vendor = models.Vendor.objects.create(name="Test Vendor", company=self.company)

    invoice = InvoiceCreationService.create_matched_invoice_data(invoice_id)

    self.assertEqual(invoice.vendor, vendor)
    # This tests WHAT the outcome is


# ❌ BAD - Testing private method implementation
def test_calculate_confidence_adds_base_score(self):
    """Test _calculate_confidence adds 0.5 base score."""
    # Don't test internal calculation steps


# ✅ GOOD - Testing public behavior with confidence threshold
def test_high_confidence_duplicates_are_marked_automatically(self):
    """Test that high confidence duplicates (≥0.9) are auto-marked."""
    original = self._create_invoice("INV-001", date=timezone.now())
    duplicate = self._create_invoice("INV-001", date=timezone.now())

    # Same number, date, and amount = high confidence
    self.assertTrue(duplicate.is_duplicate)
    self.assertGreaterEqual(duplicate.duplicate_confidence, 0.9)


# ❌ BAD - Testing method calls sequence
def test_supersede_saves_twice(self):
    """Test that supersede calls save() twice."""
    # Don't test internal save() calls


# ✅ GOOD - Testing state changes
def test_supersede_updates_both_invoice_versions(self):
    """Test that superseding updates old and new invoice states."""
    old_invoice = self._create_invoice("INV-001")
    new_invoice = self._create_invoice("INV-002")

    old_invoice.supersede(new_invoice)

    old_invoice.refresh_from_db()
    new_invoice.refresh_from_db()

    # Test the outcomes
    self.assertFalse(old_invoice.is_current)
    self.assertEqual(old_invoice.superseded_by, new_invoice)
    self.assertTrue(new_invoice.is_current)
    self.assertEqual(new_invoice.version, 2)
```

**Questions to Ask:**
- Am I testing the **outcome** or the **process**?
- If I refactor the implementation, should this test still pass?
- Does this test verify **user-visible behavior** or **code structure**?

### Don't Test Django/Framework Functionality

**DO:** Test your business logic and domain behavior

**DON'T:** Test Django ORM, validators, or framework features

```python
# ❌ BAD - Testing Django ORM
def test_invoice_saves_to_database(self):
    """Test that creating an invoice saves it."""
    invoice = Invoice.objects.create(creator_company=self.company)
    self.assertIsNotNone(invoice.id)  # Django does this automatically
    self.assertIsNotNone(invoice.time_created)  # CustomModel does this
    # You're testing Django, not your code


# ✅ GOOD - Testing your business logic
def test_invoice_creation_runs_duplicate_detection(self):
    """Test that creating an invoice triggers duplicate detection."""
    original = self._create_invoice("INV-001")
    duplicate_data = self._create_inbound_invoice_data("INV-001")

    duplicate = InvoiceCreationService.create_matched_invoice_data(duplicate_data.id)

    # Test YOUR business logic
    self.assertTrue(duplicate.is_duplicate)
    self.assertEqual(duplicate.duplicate_of, original)


# ❌ BAD - Testing Django ForeignKey behavior
def test_deleting_company_cascades_to_invoices(self):
    """Test that CASCADE deletion works."""
    # Django handles this - don't test it


# ✅ GOOD - Testing your domain constraints
def test_cannot_mark_invoice_as_duplicate_of_different_company(self):
    """Test business rule: duplicates must be from same company."""
    invoice1 = Invoice.objects.create(creator_company=self.company1)
    invoice2 = Invoice.objects.create(creator_company=self.company2)

    with self.assertRaises(ValueError) as cm:
        invoice1.mark_as_duplicate(invoice2)

    self.assertIn("same company", str(cm.exception))
```

**Framework Features You Should NOT Test:**
- Django ORM operations (create, update, delete, filter)
- Django field types (CharField, DateTimeField, ForeignKey, etc.)
- Django model inheritance (CustomModel, TimeStampedModel)
- Django signals (unless you wrote custom signal handlers)
- Django validators (unless you wrote custom validators)
- Django admin features (unless you customized them)
- Django REST Framework serializers (unless custom logic)
- Django transaction handling (unless testing your transaction boundaries)

**Your Code You SHOULD Test:**
- Business logic in service methods
- Domain model methods and properties
- Custom validation rules
- State transitions and workflows
- Integration between your services
- Data transformation and parsing
- Complex queries with business logic
- Custom permissions and access control

### No setUp - Use setUpTestData Instead

**DO:** Use `@classmethod setUpTestData(cls)` for test data that doesn't change

**DON'T:** Use `setUp(self)` instance method

```python
# ✅ GOOD - Use setUpTestData
class InvoiceCreationTests(CustomTestCase):
    @classmethod
    def setUpTestData(cls):
        """Set up test data once for the entire test class."""
        cls.company = utils.create_company(
            name="Test Company",
            contact_email="test@company.com",
            ai_ingest_email="test@ai.com",
        )
        cls.user = cls.company.employees.first()


# ❌ BAD - Don't use setUp
class InvoiceCreationTests(CustomTestCase):
    def setUp(self):
        # This runs before EVERY test, slowing down the suite
        self.company = utils.create_company(...)
```

**Why:** `setUpTestData` runs once per test class (faster), while `setUp` runs before every test method (slower). Django wraps each test in a transaction, so data created in `setUpTestData` is isolated and rolled back.

**When to use setUp:** For per-test client state like `force_login`, and for objects that are mutated by different tests and need to be reset each time. Database-persisted data that tests only read should go in `setUpTestData`.

### API Tests: setUpTestData + setUp Pattern

For API tests, prefer `setUpTestData` for shared data and keep `setUp` minimal. Make helper methods classmethods so they can be called from both `setUpTestData` and individual test methods.

```python
# ✅ Correct - data in setUpTestData, only force_login in setUp
class OutboundInvoiceCreateTests(CustomAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.invoice = cls._create_invoice()
        cls.line_item = cls._create_line_item(cls.invoice)
        cls.url = reverse("outbound_invoice")

    def setUp(self):
        self.client.force_login(self.user)

    @classmethod
    def _create_invoice(cls, **overrides):
        defaults = {"creator_company": cls.company, "currency": "USD"}
        defaults.update(overrides)
        return Invoice.objects.create(**defaults)


# ❌ Incorrect - data creation in setUp runs before every test
class OutboundInvoiceCreateTests(CustomAPITestCase):
    def setUp(self):
        self.client.force_login(self.user)
        self.invoice = self._create_invoice()  # Runs N times instead of once
        self.line_item = self._create_line_item(self.invoice)
        self.url = reverse("outbound_invoice")
```

---

## Test Organization

### Test Class Structure

Organize tests into classes grouped by functionality:

```python
class InvoiceCreationServiceTests(CustomTestCase):
    """Test business logic in InvoiceCreationService."""

    @classmethod
    def setUpTestData(cls):
        """Set up immutable test data for all tests in this class."""
        cls.company = utils.create_company(...)
        cls.user = cls.company.employees.first()

    def test_create_invoice_no_voyage(self):
        # Test implementation

    def test_missing_company_email_returns_none(self):
        # Test implementation
```

**Naming conventions:**
- Test class: `<FunctionName>Tests` for functions, `<EndpointClassName>Tests` for API endpoints
  - Examples: `GetBargesTests`, `BargeListTests`, `CreateInvoiceTests`
- Test method: `test_<what_behavior_is_being_tested>`
- Helper method: `_<helper_name>` (prefix with underscore)

### Test Method Structure (Arrange-Act-Assert)

Follow the AAA pattern:

```python
def test_mark_as_duplicate(self):
    """Test the mark_as_duplicate method."""
    # ARRANGE - Set up test data
    original = self._create_basic_invoice("INV-001")
    duplicate = self._create_basic_invoice("INV-001")

    # ACT - Perform the action being tested
    duplicate.mark_as_duplicate(original, confidence=0.95)

    # ASSERT - Verify the results
    duplicate.refresh_from_db()
    self.assertTrue(duplicate.is_duplicate)
    self.assertFalse(duplicate.is_current)
    self.assertEqual(duplicate.duplicate_of, original)
    self.assertAlmostEqual(duplicate.duplicate_confidence, 0.95, places=6)
```

---

## Base Test Classes

### CustomTestCase

Use `CustomTestCase` for all Django model/database tests:

```python
from webatds.tests.custom_test_cases import CustomTestCase


class InvoiceModelTests(CustomTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)
```

**Features:**
- Extends Django's `TestCase`
- Runs each test in a transaction (automatic rollback)
- Sets `ENVIRONMENT=test` environment variable
- Configures test-specific settings (in-memory storage, fake Redis, etc.)

**Location:** `/workspace/backend/atds/webatds/tests/custom_test_cases.py`

### CustomAPITestCase

Use `CustomAPITestCase` for API/view tests:

```python
from webatds.tests.custom_test_cases import CustomAPITestCase


class InvoiceAPIViewsTests(CustomAPITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)
        cls.client = APIClient()
```

**Features:**
- Extends Django REST Framework's `APITestCase`
- Includes all `CustomTestCase` features
- Provides `self.client` for API requests

---

## Test Data Creation

### Use Helper Methods

Create reusable helper methods for test data:

```python
class InvoiceModelTests(CustomTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)
        cls.barge = models.UnmanagedAsset.objects.create(...)

    def _create_test_invoice(self, invoice_number="INV-001", invoice_date=None):
        """Helper to create a test invoice."""
        if invoice_date is None:
            invoice_date = timezone.now()

        # Create and return invoice
        return Invoice.objects.create(
            creator_company=self.company,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
        )

    def test_invoice_creation(self):
        invoice = self._create_test_invoice("INV-123")
        self.assertEqual(invoice.invoice_number, "INV-123")
```

**Benefits:**
- Reduces code duplication
- Makes tests more readable
- Centralizes test data creation logic
- Easy to modify test data structure

### Use Test Utilities

Leverage shared utilities from `webatds.tests.utils`:

```python
from webatds.tests import utils

# Create company
company = utils.create_company(
    name="Test Company",
    contact_email="test@company.com",
    ai_ingest_email="ai@company.com",
)

# Create voyage
voyage = utils.create_voyage(company, start_port, end_port, is_active=True, name="10463272")

# Get default invoice data
data = utils.get_default_invoice_data()
```

---

## Mocking and Patching

### Mock External Services, Not Internal Logic

**DO:** Mock external dependencies (APIs, LLMs, third-party services)

**DON'T:** Mock internal business logic

```python
# ✅ GOOD - Mock external LLM service
@patch("webatds.inbound_email.services.b.GetVendorFromName")
def test_create_invoice_with_vendor_matching(self, mock_get_vendor):
    mock_get_vendor.return_value = "Test Vendor Company"

    matched_invoice = InvoiceCreationService.create_matched_invoice_data(
        self.invoice_barge_data.id
    )

    self.assertIsNotNone(matched_invoice.vendor)


# ❌ BAD - Mock internal business logic
@patch("webatds.invoicing.services.creation.InvoiceCreationService._create_invoice_atomic")
def test_invoice_creation(self, mock_atomic):
    # Don't mock the method you're trying to test
    pass
```

### Use Patch as Decorator or Context Manager

```python
# Decorator for entire test method
@patch("webatds.inbound_email.services.b.GetVendorFromName")
def test_with_decorator(self, mock_vendor):
    mock_vendor.return_value = "Test Vendor"
    # Test code


# Context manager for specific section
def test_with_context_manager(self):
    with patch("webatds.invoicing.services.creation.logger.warning") as mock_logger:
        result = InvoiceCreationService.create_matched_invoice_data(999)
        mock_logger.assert_called_once_with("No inbound invoice found with ID %s", 999)
```

### Mock at the Right Level

Mock at the boundary between your code and external systems:

```python
# ✅ GOOD - Mock at the service boundary
@patch("webatds.inbound_email.services.VendorMatchingService.find_vendor_match")
def test_vendor_resolution(self, mock_find):
    mock_find.return_value = (vendor_object, True)
    # Test code

# ❌ BAD - Mock too deep in the implementation
@patch("webatds.inbound_email.services.some_internal_helper")
def test_vendor_resolution(self, mock_helper):
    # This is too implementation-specific
```

### Verify Mocks Are Being Used Correctly

**Always verify that mocks are called and return values are used:**

```python
# ✅ GOOD - Verify mock was called and result was used
@patch("webatds.inbound_email.services.b.GetVendorFromName")
def test_vendor_matching_uses_llm_result(self, mock_get_vendor):
    """Test that vendor matching uses the LLM result."""
    mock_get_vendor.return_value = "Acme Corporation"

    invoice = InvoiceCreationService.create_matched_invoice_data(invoice_id)

    # Verify mock was called
    mock_get_vendor.assert_called_once()

    # Verify the result was actually used (test behavior)
    self.assertIsNotNone(invoice.vendor)
    self.assertEqual(invoice.vendor.name, "Acme Corporation")
```

**Verify mock call arguments:**

```python
# ✅ GOOD - Verify exact arguments
@patch("webatds.inbound_email.services.VendorMatchingService.find_vendor_match")
def test_vendor_matching_passes_correct_arguments(self, mock_find):
    """Test that vendor matching receives correct company and name."""
    vendor_object = models.Vendor.objects.create(name="Test Vendor", company=self.company)
    mock_find.return_value = (vendor_object, False)

    invoice_data = self._create_inbound_invoice_data()
    invoice_data.vendor = "Test Vendor"
    invoice_data.save()

    invoice = InvoiceCreationService.create_matched_invoice_data(invoice_data.id)

    # Verify mock was called with correct arguments
    mock_find.assert_called_once_with(
        "Test Vendor",  # vendor_name
        self.company,  # company
        allow_llm=True,  # allow_llm flag
    )

    # Verify result was used
    self.assertEqual(invoice.vendor, vendor_object)
```

**Verify mock call count:**

```python
# ✅ GOOD - Verify exact call count
@patch("webatds.inbound_email.services.VendorMatchingService.find_vendor_match")
def test_invoice_with_three_line_item_vendors(self, mock_find):
    """Test that each line item vendor triggers vendor matching."""
    mock_find.return_value = (vendor_object, False)

    # Create invoice with 3 line items, each with different vendor
    invoice_data = self._create_inbound_invoice_data()
    for i in range(3):
        inbound_email_services.create_invoice_line_item(
            invoice=invoice_data,
            description=f"Service {i}",
            line_total=100.0,
            vendor=f"Vendor {i}",
        )

    invoice = InvoiceCreationService.create_matched_invoice_data(invoice_data.id)

    # Verify vendor matching was called 3 times (once per line item vendor)
    self.assertEqual(mock_find.call_count, 3)
```

**Mock Guidelines Summary:**

1. **Always verify mocks are called**: Use `assert_called()`, `assert_called_once()`, or `assert_not_called()`
2. **Verify arguments**: Use `assert_called_with()` or `assert_called_once_with()`
3. **Verify call count**: Use `call_count` when multiple calls expected
4. **Verify behavior**: Don't just test that mock was called, test that the result was used correctly
5. **Use side_effect for multiple calls**: When mock is called multiple times with different returns
6. **Verify exceptions**: Test both that exception is raised AND behavior (like rollback)
7. **Don't mock what you're testing**: Mock external dependencies, not your own code
8. **Mock at boundaries**: Mock at the edge of your system (APIs, services), not internal helpers

---

## Assertions

### Use Descriptive Assertions

Choose the most specific assertion for your test:

```python
# ✅ GOOD - Specific assertions
self.assertEqual(invoice.invoice_number, "INV-001")
self.assertTrue(invoice.is_duplicate)
self.assertIsNone(invoice.vendor)
self.assertIn(barge, matched_barges)
self.assertGreaterEqual(confidence, 0.9)
self.assertAlmostEqual(amount, Decimal("123.45"), places=2)

# ❌ BAD - Generic assertions
self.assertTrue(invoice.invoice_number == "INV-001")  # Use assertEqual
self.assertFalse(invoice.vendor)  # Use assertIsNone
```

### Test Both Success and Failure Cases

```python
def test_mark_as_duplicate_success(self):
    """Test successful duplicate marking."""
    original = self._create_invoice("INV-001")
    duplicate = self._create_invoice("INV-001")

    duplicate.mark_as_duplicate(original, confidence=0.95)

    self.assertTrue(duplicate.is_duplicate)
    self.assertEqual(duplicate.duplicate_of, original)


def test_mark_as_duplicate_of_self_raises_error(self):
    """Test that marking an invoice as duplicate of itself raises an error."""
    invoice = self._create_invoice("INV-001")

    with self.assertRaises(ValueError) as context:
        invoice.mark_as_duplicate(invoice, confidence=0.95)

    self.assertEqual(
        str(context.exception), "An invoice cannot be marked as a duplicate of itself"
    )
```

### Verify Database State Changes

Use `refresh_from_db()` to verify database changes:

```python
def test_invoice_status_update(self):
    """Test that invoice status is updated in the database."""
    invoice = self._create_invoice("INV-001")

    invoice.is_current = False
    invoice.save(update_fields=["is_current"])

    # Refresh to verify database state
    invoice.refresh_from_db()
    self.assertFalse(invoice.is_current)
```

---

## Test Documentation

### Docstrings Are Optional - Keep Test Names Descriptive

**Tests don't require docstrings.** A well-named test method should be self-explanatory.

```python
# ✅ GOOD - Descriptive name, no docstring needed
def test_mark_as_duplicate_sets_flags_and_links_to_original(self):
    original = self._create_basic_invoice("INV-001")
    duplicate = self._create_basic_invoice("INV-001")

    duplicate.mark_as_duplicate(original, confidence=0.95)

    duplicate.refresh_from_db()
    self.assertTrue(duplicate.is_duplicate)
    self.assertFalse(duplicate.is_current)
    self.assertEqual(duplicate.duplicate_of, original)


# ✅ ACCEPTABLE - Short one-line docstring for clarity
def test_mark_as_duplicate(self):
    """Test marking an invoice as duplicate sets correct flags and links."""
    # Test implementation


# ❌ BAD - Verbose multi-line docstring
def test_mark_as_duplicate(self):
    """Test the mark_as_duplicate method.

    Verifies that marking an invoice as duplicate sets the correct flags,
    links to the original invoice, and stores the confidence score.
    This is important for our duplicate detection workflow.
    """
    # Test implementation - docstring is unnecessarily long
```

### Use Descriptive Test Names

```python
# ✅ GOOD - Names describe the behavior
def test_high_confidence_duplicate_detection(self):
def test_missing_company_email_returns_none(self):
def test_supersede_clears_duplicate_flags(self):

# ❌ BAD - Names don't describe behavior
def test_invoice_1(self):
def test_duplicate(self):
def test_update(self):
```

---

## Testing Patterns by Type

### Unit Tests - Business Logic

Test individual methods/functions in isolation:

```python
class ParseCurrencyAndAmountTests(CustomTestCase):
    """Test cases for the parse_currency_and_amount function."""

    def test_usd_dollar_symbol_parsing(self):
        """Test parsing USD currency with $ symbol."""
        currency, amount = parse_currency_and_amount("$20.00")

        self.assertEqual(currency, Currency.USD)
        self.assertEqual(amount, Decimal("20.00"))

    def test_invalid_input_parsing(self):
        """Test parsing invalid inputs returns None."""
        test_cases = [
            "invalid",
            "",
            None,
            "abc$def",
            "$$20.00",
        ]

        for test_input in test_cases:
            with self.subTest(input=test_input):
                currency, amount = parse_currency_and_amount(test_input)
                self.assertIsNone(currency)
                self.assertIsNone(amount)
```

**Use `subTest` for parameterized tests:**

```python
def test_multiple_scenarios(self):
    """Test multiple related scenarios."""
    test_cases = [
        ("$20.00", Currency.USD, Decimal("20.00")),
        ("€15.50", Currency.EUR, Decimal("15.50")),
        ("£100.00", Currency.GBP, Decimal("100.00")),
    ]

    for test_input, expected_currency, expected_amount in test_cases:
        with self.subTest(input=test_input):
            currency, amount = parse_currency_and_amount(test_input)
            self.assertEqual(currency, expected_currency)
            self.assertEqual(amount, expected_amount)
```

### Integration Tests - Service Interactions

Test interactions between multiple components:

```python
class InvoiceCreationServiceTests(CustomTestCase):
    """Test business logic in InvoiceCreationService."""

    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)
        cls.barge = models.UnmanagedAsset.objects.create(...)

    @patch("webatds.inbound_email.services.b.GetVendorFromName")
    def test_create_invoice_with_vendor_matching(self, mock_get_vendor):
        """Test that vendor matching works when a vendor exists."""
        # Create test vendor
        test_vendor = models.Vendor.objects.create(
            name="Test Vendor Company",
            company=self.company,
        )

        mock_get_vendor.return_value = "Test Vendor Company"

        # Create invoice (integrates multiple services)
        matched_invoice = InvoiceCreationService.create_matched_invoice_data(
            self.invoice_barge_data.id
        )

        # Verify vendor was matched
        self.assertIsNotNone(matched_invoice.vendor)
        self.assertEqual(matched_invoice.vendor, test_vendor)
```

### Transaction Tests - Atomicity

Test that transactions rollback on failure:

```python
class InvoiceCreationServiceTests(CustomTestCase):
    """Test transaction behavior in InvoiceCreationService."""

    def test_transaction_rollback_on_duplicate_detection_failure(self):
        """Test that invoice creation is rolled back if duplicate detection fails."""
        invoice_data = self._create_test_inbound_invoice_data("INV-ROLLBACK")

        initial_invoice_count = Invoice.objects.count()
        initial_line_item_count = InvoiceLineItem.objects.count()

        # Mock duplicate detection to raise an exception
        with patch(
            "webatds.invoicing.services.creation.InvoiceDuplicateDetector.detect_duplicates"
        ) as mock_detector:
            mock_detector.side_effect = RuntimeError("Duplicate detection failed!")

            # Attempt to create invoice - should raise exception
            with self.assertRaises(RuntimeError) as cm:
                InvoiceCreationService.create_matched_invoice_data(invoice_data.id)

            self.assertEqual(str(cm.exception), "Duplicate detection failed!")

        # Verify transaction was rolled back - no new records created
        self.assertEqual(Invoice.objects.count(), initial_invoice_count)
        self.assertEqual(InvoiceLineItem.objects.count(), initial_line_item_count)
```

### Model Tests - Domain Logic

Test model methods and properties:

```python
class InvoiceModelTests(CustomTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)

    def test_get_total_amount_with_line_items(self):
        """Test get_total_amount calculation from line items."""
        invoice = Invoice.objects.create(creator_company=self.company)

        invoice.add_line_item(description="Service 1", line_total=100.0)
        invoice.add_line_item(description="Service 2", line_total=75.0)

        total = invoice.get_total_amount()
        self.assertEqual(total, 175.0)
```

---

## Edge Cases and Error Handling

### Test Boundary Conditions

```python
def test_zero_amount_parsing(self):
    """Test parsing zero amounts."""
    currency, amount = parse_currency_and_amount("$0.00")
    self.assertEqual(currency, Currency.USD)
    self.assertEqual(amount, Decimal("0.00"))


def test_large_amount_parsing(self):
    """Test parsing large amounts with commas."""
    currency, amount = parse_currency_and_amount("$1,234,567.89")
    self.assertEqual(currency, Currency.USD)
    self.assertEqual(amount, Decimal("1234567.89"))
```

### Test Error Conditions

```python
def test_mark_as_duplicate_of_self_raises_error(self):
    """Test that marking an invoice as duplicate of itself raises an error."""
    invoice = self._create_invoice("INV-001")

    with self.assertRaises(ValueError) as context:
        invoice.mark_as_duplicate(invoice, confidence=0.95)

    self.assertEqual(
        str(context.exception), "An invoice cannot be marked as a duplicate of itself"
    )


def test_missing_required_data_returns_none(self):
    """Test that missing required data returns None gracefully."""
    with patch("webatds.invoicing.services.creation.logger.warning") as mock_logger:
        result = InvoiceCreationService.create_matched_invoice_data(99999)

        self.assertIsNone(result)
        mock_logger.assert_called_once_with("No inbound invoice found with ID %s", 99999)
```

### Test Null/Empty Values

```python
def test_get_total_amount_with_no_line_items(self):
    """Test get_total_amount when invoice has no line items."""
    invoice = self._create_basic_invoice()

    total = invoice.get_total_amount()
    self.assertEqual(total, 0)
```

---

## Test Isolation and Independence

### Each Test Should Be Independent

```python
# ✅ GOOD - Tests are independent
class InvoiceModelTests(CustomTestCase):
    def test_create_invoice(self):
        invoice = Invoice.objects.create(...)
        self.assertIsNotNone(invoice)

    def test_update_invoice(self):
        # Create fresh invoice for this test
        invoice = Invoice.objects.create(...)
        invoice.is_current = False
        invoice.save()
        self.assertFalse(invoice.is_current)


# ❌ BAD - Tests depend on each other
class InvoiceModelTests(CustomTestCase):
    def test_create_invoice(self):
        self.invoice = Invoice.objects.create(...)

    def test_update_invoice(self):
        # Depends on test_create_invoice running first
        self.invoice.is_current = False
        invoice.save()
```

### Don't Share Mutable State

```python
# ✅ GOOD - Each test creates its own data
def test_invoice_update(self):
    invoice = self._create_invoice()
    invoice.is_current = False
    invoice.save()


# ❌ BAD - Tests modify shared class state
@classmethod
def setUpTestData(cls):
    cls.invoice = Invoice.objects.create(...)


def test_invoice_update(self):
    self.invoice.is_current = False  # Modifies shared state
    self.invoice.save()
```

---

## Performance Considerations

### Use setUpTestData for Immutable Data

```python
# ✅ GOOD - Company created once per test class
@classmethod
def setUpTestData(cls):
    cls.company = utils.create_company(...)


# ❌ BAD - Company created for every test
def setUp(self):
    self.company = utils.create_company(...)
```

### Use Bulk Operations When Possible

```python
# ✅ GOOD - Bulk create for multiple objects
test_invoices = [
    Invoice(creator_company=self.company, invoice_number=f"INV-{i}") for i in range(10)
]
Invoice.objects.bulk_create(test_invoices)

# ❌ BAD - Individual creates in loop
for i in range(10):
    Invoice.objects.create(creator_company=self.company, invoice_number=f"INV-{i}")
```

---

## Anti-Patterns to Avoid

### Don't Test Framework Code

```python
# ❌ BAD - Testing Django's ORM
def test_django_creates_invoice(self):
    invoice = Invoice.objects.create(...)
    self.assertIsNotNone(invoice.id)  # Django does this automatically


# ✅ GOOD - Test your business logic
def test_invoice_marked_as_duplicate_on_creation(self):
    original = self._create_invoice("INV-001")
    duplicate = InvoiceCreationService.create_matched_invoice_data(...)
    self.assertTrue(duplicate.is_duplicate)
```

### Don't Mock What You're Testing

```python
# ❌ BAD - Mocking the method being tested
@patch("webatds.invoicing.services.creation.InvoiceCreationService.create_matched_invoice_data")
def test_invoice_creation(self, mock_create):
    mock_create.return_value = Mock()
    # You're not actually testing anything!


# ✅ GOOD - Test the actual method
def test_invoice_creation(self):
    result = InvoiceCreationService.create_matched_invoice_data(...)
    self.assertIsNotNone(result)
```

### Don't Test Multiple Behaviors in One Test

```python
# ❌ BAD - Testing too many things
def test_invoice_creation_and_duplicate_detection_and_versioning(self):
    # Creates invoice
    # Checks duplicate detection
    # Verifies versioning
    # Tests line item creation
    # Way too much in one test!

# ✅ GOOD - One behavior per test
def test_invoice_creation_with_vendor(self):
    """Test invoice is created with vendor assigned."""
    # Focus on vendor assignment

def test_duplicate_detection_on_creation(self):
    """Test duplicate detection runs during creation."""
    # Focus on duplicate detection
```

---

## Pragmatic Test Coverage

### Balance Comprehensive Testing with Test Efficiency

**DO:** Write tests that efficiently cover multiple scenarios when those scenarios naturally overlap

**DON'T:** Write redundant tests that slow down the suite without adding value

```python
# ✅ GOOD - One test covers multiple aspects efficiently
def test_multipage_doc_file_parsing(self):
    """Test parsing multipage DOC file (covers both DOC format and multipage handling)."""
    doc_path = "test_files/multipage_invoice.doc"
    pages = parse_document(doc_path)

    self.assertEqual(len(pages), 3)
    self.assertIsNotNone(pages[0].text)
    self.assertIsNotNone(pages[2].text)

# ❌ BAD - Redundant single-page tests for every format
def test_pdf_parsing(self):
def test_doc_parsing(self):
def test_docx_parsing(self):
# All test the same thing with different extensions
```

**Guidelines:**
1. Ask yourself: "Does this test validate unique behavior, or am I just changing test data?"
2. Prefer variation: Test the same code path with meaningfully different inputs
3. Avoid permutation explosion: Don't test every combination unless there's complex interaction logic
4. Focus on boundaries: Test edge cases (empty, very large, malformed) rather than multiple "normal" cases

---

## Test File Organization

```
tests/
├── __init__.py
├── custom_test_cases.py                # Base test classes
├── utils.py                            # Shared test utilities
├── invoicing/
│   ├── __init__.py
│   ├── test_models.py                  # Invoice model tests
│   └── services/
│       ├── test_creation.py            # Invoice creation service tests
│       ├── test_duplicate_detection.py # Duplicate detection tests
│       └── test_query.py               # Query service tests
├── inbound_email/
│   ├── test_models.py
│   ├── test_services.py
│   └── pipelines/
│       └── barge/
│           └── steps/
│               └── test_extract_invoice_groups_step.py
└── integrations/
    └── providers/
        └── veson/
            ├── test_handlers.py
            └── test_tasks.py
```

**Naming convention:**
- Test files: `test_<module_name>.py`
- Test directories mirror source code structure

---

## Summary

**Key Principles:**
1. Test behavior, not implementation
2. Use `setUpTestData`, not `setUp`
3. Each test should be independent
4. Mock external services, not internal logic
5. Use descriptive names
6. Follow Arrange-Act-Assert pattern
7. Test success, failure, and edge cases
8. Verify database state with `refresh_from_db()`
9. Write efficient tests that cover multiple scenarios when natural
10. Avoid redundant tests that slow down the suite

---

## Related Documentation

- **Django Testing:** https://docs.djangoproject.com/en/stable/topics/testing/
- **Django REST Framework Testing:** https://www.django-rest-framework.org/api-guide/testing/
- **Python unittest:** https://docs.python.org/3/library/unittest.html
- **Custom Test Cases:** `/workspace/backend/atds/webatds/tests/custom_test_cases.py`
