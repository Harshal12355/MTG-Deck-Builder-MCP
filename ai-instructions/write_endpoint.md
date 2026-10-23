# Writing API Endpoints

## Quick Reference

When creating or modifying API endpoints, follow these patterns.

### Pre-Flight Checklist

Before writing an endpoint:
1. Read [conventions.md](./conventions.md) for naming and coding conventions
2. Find a similar existing endpoint as reference
3. Identify whether this is a list, detail, or action endpoint
4. Check module-specific AGENTS.md for domain conventions
5. Ensure `serializer_class` / `@extend_schema` accurately describe both request and response shapes — drf-spectacular uses these to generate TypeScript types

---

## View Structure

#### List View
```python
class InvoiceList(generics.ListCreateAPIView):
    """List and create invoices."""

    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Invoice.objects.filter(creator_company=self.request.user.company)
            .select_related("vendor")
            .prefetch_related("line_items")
        )
```

#### Detail View
```python
class InvoiceDetail(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an invoice."""

    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(creator_company=self.request.user.company)
```

#### Action View
```python
class InvoiceApprove(generics.GenericAPIView):
    """Approve an invoice."""

    serializer_class = InvoiceApproveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(creator_company=self.request.user.company)

    def post(self, request, pk):
        invoice = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Business logic here
        invoice.approve(approved_by=request.user)

        return Response(InvoiceSerializer(invoice).data)
```

## Serializer Patterns

### Basic Serializer

```python
class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "total", "status", "vendor"]
        read_only_fields = ["id", "status"]
```

### Separate Serializers for Create and Update

**Use separate serializers for create and update operations instead of manual validation.**

This pattern provides precise OpenAPI schemas and leverages DRF's automatic validation instead of custom logic.

```python
# 1. Base Serializer - For reading/displaying
class LineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ["id", "description", "amount"]


# 2. Create Serializer - Required fields enforced
class LineItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ["description", "amount"]  # No id


# 3. Update Serializer - Partial updates allowed
class LineItemUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ["id", "description", "amount"]
        extra_kwargs = {
            "id": {"read_only": False, "required": True},
            "description": {"required": False},
            "amount": {"required": False},
        }


# 4. Polymorphic Router - Routes to create or update based on id presence
class LineItemWriteSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        has_id = data.get("id") is not None  # Explicit check handles id=0
        if has_id:
            serializer = LineItemUpdateSerializer(data=data, context=self.context)
        else:
            serializer = LineItemCreateSerializer(data=data, context=self.context)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data

    def to_representation(self, instance):
        return LineItemSerializer(instance, context=self.context).data


# 5. Parent Serializer - Uses polymorphic router
class InvoiceSerializer(serializers.ModelSerializer):
    line_items = LineItemWriteSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = ["id", "invoice_number", "line_items"]
```

#### Benefits

- **Precise OpenAPI Schemas**: Create schema shows required fields as non-nullable; update schema shows them as optional for PATCH
- **No Manual Validation**: DRF automatically validates based on serializer structure
- **Better Error Messages**: DRF generates proper field-level validation errors
- **Type Safety**: Required fields enforced at serializer level, catches errors before database

#### Example API Behavior

**Creating Line Item:**
```json
POST /api/invoice/123/
{
    "line_items": [
        {"description": "Service", "line_total": 1000.00}
    ]
}
```
Missing required field → Clean 400 validation error (not 500 IntegrityError)

**Updating Line Item:**
```json
PATCH /api/invoice/123/
{
    "line_items": [
        {"id": 456, "quantity": 5}
    ]
}
```
Partial update - only id required, other fields optional.

#### When to Use

- Nested resources in create/update operations
- Required fields differ between create and update
- Using DDD aggregate pattern (all operations through parent)
- You want accurate OpenAPI schema generation

#### When NOT to Use

- Separate endpoints for create and update (use view-level serializer selection)
- All fields have the same requirements for create and update
- Resources are not nested

### Permission Patterns

```python
from rest_framework.permissions import IsAuthenticated


class InvoiceList(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # Always filter by user's company
        return Invoice.objects.filter(creator_company=self.request.user.company)
```

### Query Parameter Filtering

**Use django-filter for query param filtering instead of manual `request.query_params` parsing.**

django-filter handles type coercion consistently (e.g., `"true"`, `"True"`, `"1"` all work for booleans) and auto-generates the OpenAPI schema — no manual `@extend_schema` params needed.

```python
# ✅ Correct - use django-filter
from django_filters import rest_framework as filters
from django_filters.rest_framework import DjangoFilterBackend


class CostAllocationFilter(filters.FilterSet):
    voyage_id = filters.NumberFilter(field_name="voyage_id", required=True)
    billed = filters.BooleanFilter(field_name="billed")

    class Meta:
        model = CostAllocation
        fields = ["voyage_id", "billed"]


class CostAllocationList(generics.GenericAPIView, mixins.ListModelMixin):
    filter_backends = [DjangoFilterBackend]
    filterset_class = CostAllocationFilter

    def get_queryset(self):
        # Only base queryset logic here — no manual param filtering
        return CostAllocation.objects.filter(
            voyage__company=self.request.user.company,
        ).select_related("voyage")
```

```python
# ❌ Incorrect - manual parsing, no schema, inconsistent boolean handling
def get_queryset(self):
    voyage_id = self.request.query_params.get("voyage_id")
    billed = self.request.query_params.get("billed")
    qs = CostAllocation.objects.filter(voyage_id=voyage_id)
    if billed is not None:
        qs = qs.filter(billed=billed.lower() == "true")
    return qs
```

Use `@extend_schema` with `OpenApiParameter` only for query params that can't be expressed as django-filter fields (e.g., params that control response shape rather than filtering).

### Query Optimization

```python
def get_queryset(self):
    return (
        Invoice.objects.filter(creator_company=self.request.user.company)
        .select_related(
            "vendor",
            "created_by",
        )
        .prefetch_related(
            "line_items",
            "line_items__barges",
        )
    )
```

### Response Patterns

```python
from rest_framework.response import Response
from rest_framework import status

# Success with data
return Response(serializer.data)

# Created
return Response(serializer.data, status=status.HTTP_201_CREATED)

# No content
return Response(status=status.HTTP_204_NO_CONTENT)

# Error
return Response({"error": "Description"}, status=status.HTTP_400_BAD_REQUEST)
```

### File Organization

```
webatds/
└── invoicing/
    ├── api_views.py      # View classes
    ├── serializers.py    # Serializer classes
    └── urls.py           # URL patterns
```

### Testing Your Endpoint

After creating an endpoint, write tests following `write_tests.md`:

```python
class InvoiceListTests(CustomAPITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = utils.create_company(...)
        cls.user = cls.company.employees.first()

    def test_list_returns_only_company_invoices(self):
        self.client.force_login(user=self.user)

        response = self.client.get(reverse("invoice"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for invoice in response.data:
            self.assertEqual(invoice["company"], self.company.id)
```

---

## Anti-Patterns

| Don't | Do Instead |
|-------|------------|
| Manual validation in `validate()` for create vs update | Use separate serializers |
| Raw SQL in views | Use ORM with `select_related`/`prefetch_related` |
| Return 500 for validation errors | Let DRF handle with 400 |

### Manual Validation Anti-Pattern

```python
# ❌ Don't do this
class LineItemSerializer(serializers.ModelSerializer):
    class Meta:
        extra_kwargs = {
            "description": {"required": False},
            "line_total": {"required": False},
        }

    def validate(self, data):
        is_create = "id" not in data
        if is_create:
            if "description" not in data:
                raise ValidationError({"description": "Required for create"})
            if "line_total" not in data:
                raise ValidationError({"line_total": "Required for create"})
        return data
```

**Problems:**
- OpenAPI schema shows all fields as optional (misleading)
- Manual validation logic to maintain
- Inconsistent error messages
- Harder to test
