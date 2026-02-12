Optimizing tool selection...I'll analyze the current structure and create a comprehensive production-ready folder structure plan.   

Read [](file:///Users/surya96t/Documents/projects/personal-projs/personal-ai-finance/backend)

Read [](file:///Users/surya96t/Documents/projects/personal-projs/personal-ai-finance/backend/app/routers.py#1-1), lines 1 to 30

Read [](file:///Users/surya96t/Documents/projects/personal-projs/personal-ai-finance/backend/app/main.py#100-100), lines 100 to 150

Searched for regex `@router\.(get|post|put|delete|patch)` (`**/backend/app/routers.py`), 3 results

Searched for regex `@app\.(get|post|put|delete|patch)` (`**/backend/app/main.py`), 6 results

Searched for regex `@inngest_client\.create_function` (`**/backend/app/inngest_functions.py`), 5 results

## **Production-Ready Backend Folder Structure Plan**

### **Architecture Decision (Updated Feb 11, 2026)**

**Stack Simplification:**
- ✅ **Storage:** Supabase Storage (replacing Google Cloud Storage)
- ✅ **OCR:** OpenAI GPT-4o Vision (replacing Google Vision API)
- ✅ **AI Processing:** OpenAI GPT-4o-mini (replacing Google Gemini)
- ❌ **Encryption:** Removed KMS complexity (using Supabase native encryption)
- ✅ **Database:** Supabase PostgreSQL (kept)
- ✅ **Auth:** Clerk (kept)
- ✅ **Workflows:** Inngest (kept)

**Benefits:** Fewer vendors, lower cost, simpler architecture, better integration

---

### **Current State Analysis**

**Endpoints:**
- main.py: 6 endpoints (root, documents x3, transactions x2)
- routers.py: 3 dashboard endpoints
- inngest_functions.py: 5 workflow functions
- All in flat structure with mixed concerns

---

## **Proposed Production Structure**

```
backend/
├── .env
├── .gitkeep
├── requirements.txt
├── README.md
│
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI app initialization, middleware, Inngest registration
│   ├── config.py                  # Configuration & settings (keep as-is, expand)
│   │
│   ├── api/                       # API Layer - All HTTP endpoints
│   │   ├── __init__.py
│   │   ├── deps.py                # API-specific dependencies (auth, pagination, etc.)
│   │   └── v1/                    # API versioning
│   │       ├── __init__.py
│   │       ├── router.py          # Main V1 router aggregator
│   │       └── endpoints/         # Endpoint modules by domain
│   │           ├── __init__.py
│   │           ├── documents.py   # Document upload/list/process endpoints
│   │           ├── transactions.py # Transaction CRUD endpoints
│   │           └── dashboard.py   # Dashboard analytics endpoints
│   │
│   ├── core/                      # Core business logic & infrastructure
│   │   ├── __init__.py
│   │   ├── auth.py                # Clerk authentication logic
│   │   ├── cache.py               # Cache service (from cache_service.py)
│   │   └── storage.py             # Supabase Storage client & operations
│   │
│   ├── db/                        # Database layer
│   │   ├── __init__.py
│   │   ├── client.py              # Supabase client initialization
│   │   └── repositories/          # Data access patterns
│   │       ├── __init__.py
│   │       ├── base.py            # Base repository with common methods
│   │       ├── documents.py       # Document table operations
│   │       └── transactions.py    # Transaction table operations
│   │
│   ├── models/                    # Pydantic models & schemas
│   │   ├── __init__.py
│   │   ├── requests.py            # Request models (DocumentProcessRequest, etc.)
│   │   ├── responses.py           # Response models
│   │   └── domain.py              # Domain models (Transaction, Document, etc.)
│   │
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── document_service.py    # Document business logic
│   │   ├── transaction_service.py # Transaction business logic
│   │   └── dashboard_service.py   # Dashboard calculations & aggregations
│   │
│   ├── workflows/                 # Inngest workflows (async jobs)
│   │   ├── __init__.py
│   │   ├── client.py              # Inngest client (from clients.py)
│   │   └── functions/             # Individual workflow functions
│   │       ├── __init__.py
│   │       ├── document_processing.py  # Step 1: process_document_uploaded
│   │       ├── ocr_extraction.py       # Step 2: perform_ocr_on_document
│   │       ├── line_isolation.py       # Step 3: isolate_transaction_lines
│   │       ├── data_structuring.py     # Step 4: structure_transaction_data
│   │       └── enrichment.py           # Step 5: enrich_and_categorize_transactions
│   │
│   ├── integrations/              # External service integrations
│   │   ├── __init__.py
│   │   └── openai.py              # OpenAI client for Vision & AI processing
│   │
│   ├── utils/                     # Utility functions & helpers
│   │   ├── __init__.py
│   │   ├── datetime.py            # Date/time utilities
│   │   ├── calculations.py        # Financial calculations
│   │   └── validators.py          # Custom validators
│   │
│   └── middleware/                # Custom middleware (optional for now)
│       ├── __init__.py
│       └── error_handler.py       # Global error handling
│
└── tests/                         # Tests mirroring source structure
    ├── __init__.py
    ├── conftest.py                # Pytest fixtures
    ├── unit/                      # Unit tests
    │   ├── __init__.py
    │   ├── test_cache.py
    │   ├── test_calculations.py
    │   └── services/
    │       ├── test_dashboard_service.py
    │       └── test_transaction_service.py
    ├── integration/               # Integration tests
    │   ├── __init__.py
    │   └── api/
    │       ├── test_documents_api.py
    │       ├── test_transactions_api.py
    │       └── test_dashboard_api.py
    └── fixtures/                  # Test data & mocks
        ├── __init__.py
        └── sample_data.py
```

---

## **Migration Mapping (File Reorganization)**

### **Phase 1: Core Infrastructure**
| Current File | New Location | Purpose |
|-------------|--------------|---------|
| `app/config.py` | `app/config.py` | **Keep** - expand with settings class |
| `app/cache_service.py` | `app/core/cache.py` | Cache logic |
| `app/clients.py` | `app/workflows/client.py` | Inngest client |
| `app/dependencies.py` | Split into 3 files: | |
| - Auth logic | `app/core/auth.py` | Clerk verification |
| - Supabase client | `app/db/client.py` | DB client |
| - fetch transactions | `app/services/transaction_service.py` | Business logic (no encryption) |
| ~~`app/encryption_service.py`~~ | ❌ **REMOVED** | No longer using KMS encryption |

### **Phase 2: API Layer**
| Current File | New Location | Purpose |
|-------------|--------------|---------|
| `app/main.py` (endpoints) | Split into 3 files: | |
| - Root endpoint | `app/main.py` | Keep minimal |
| - Document endpoints | `app/api/v1/endpoints/documents.py` | 3 endpoints |
| - Transaction endpoints | `app/api/v1/endpoints/transactions.py` | 2 endpoints |
| `app/routers.py` | `app/api/v1/endpoints/dashboard.py` | 3 dashboard endpoints |

### **Phase 3: Workflows**
| Current File | New Location | Purpose |
|-------------|--------------|---------|
| `app/inngest_functions.py` | Split into 5 files in `app/workflows/functions/`: | |
| - Function 1 | `document_processing.py` | Upload handler |
| - Function 2 | `ocr_extraction.py` | OCR using OpenAI Vision |
| - Function 3 | `line_isolation.py` | AI isolation using OpenAI |
| - Function 4 | `data_structuring.py` | AI structuring using OpenAI |
| - Function 5 | `enrichment.py` | AI enrichment using OpenAI |

### **Phase 4: Models & Services**
| What | New Location | Purpose |
|------|--------------|---------|
| Pydantic models from `app/main.py` | `app/models/requests.py` | Request DTOs |
| Pydantic models from `app/inngest_functions.py` | `app/models/domain.py` | Domain models |
| Dashboard calculations from `app/routers.py` | `app/services/dashboard_service.py` | Business logic |
| Transaction operations from `app/dependencies.py` | `app/services/transaction_service.py` | Business logic (simplified, no encryption) |

---

## **Key Benefits**

### **1. Separation of Concerns**
- **API Layer** (`api/`) - HTTP handling only
- **Business Logic** (`services/`) - Domain logic
- **Data Access** (`db/`) - Database operations
- **Infrastructure** (`core/`) - Cross-cutting concerns

### **2. Scalability**
- Easy to add new endpoints without cluttering main.py
- Each workflow function in its own file for clarity
- Room for new features (budgets, goals, reports)

### **3. Testability**
- Clear boundaries for unit vs integration tests
- Services can be tested independently
- Mock dependencies easily

### **4. Maintainability**
- Similar code grouped together
- Easy to locate functionality
- Clear import paths

### **5. Team Collaboration**
- Multiple developers can work on different domains
- Reduced merge conflicts
- Clear ownership of modules

---

## **Migration Strategy (When Ready)**

### **Phase 1: Infrastructure (No Breaking Changes)**
1. Create new folder structure
2. Copy files to new locations
3. Update imports in new files
4. Keep old files temporarily

### **Phase 2: Update main.py**
1. Import routers from new locations
2. Update Inngest function imports
3. Test all endpoints

### **Phase 3: Clean Up**
1. Delete old files
2. Run full test suite
3. Update documentation

### **Phase 4: Add Missing Pieces**
1. Create repository layer for DB ops
2. Add proper response models
3. Implement base classes
4. Add middleware

---

## **Critical Considerations**

✅ **No breaking changes** - All imports will be updated atomically
✅ **Backward compatible** - API contracts remain unchanged
✅ **Testable migration** - Can verify each phase independently
✅ **Rollback ready** - Can revert to old structure if issues arise

**Estimated effort:** 2-3 hours for careful migration
**Risk level:** Low (if done methodically with testing)

---

Would you like me to proceed with implementing this structure once you have the environment variables ready?