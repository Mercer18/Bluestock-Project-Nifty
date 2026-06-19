# Sprint 1 Master Plan: Foundation & ETL Pipeline

This is the master coordination document for the **Nifty 100 Financial Intelligence Platform - Sprint 1 (Foundation & ETL)**. It acts as the central reference point, guiding the project execution from **June 17, 2026** to the deadline on **June 22, 2026**.

---

## 1. Objectives & Goals
The objective of Sprint 1 is to establish a robust, production-grade **data foundation** for the Nifty 100 Financial Intelligence Platform. This involves reading, normalising, validating, and loading **12 datasets (7 Core + 5 Supplementary)** containing ~11,000+ data points across 92 companies into a unified **SQLite relational database** with zero critical data quality (DQ) violations and >=80% test coverage.

### Key Targets:
- **Ingestion**: Standardize and load 7 core files (e.g., balance sheets, cash flows, profit & loss) and 5 supplementary files (e.g., stock prices, sector mapping, market caps).
- **Quality**: Enforce 16 Data Quality rules, logging all warnings/errors, and ensuring zero critical schema violations.
- **Relational Storage**: Design a 10-table relational database structure with enforced foreign key constraints.
- **Verification**: Write 60+ unit tests with `pytest` for all normalisation and validation routines.

---

## 2. Directory Structure & Document Navigation
To maintain organization, planning documents are stored in the `ProjectNifty/planning/` folder. Use the following links to navigate the detailed plans:

*   📅 **[Day-Wise Execution Plan](file:///x:/CODING/PROJECTS/InternshipWork/Bluestock/ProjectNifty/planning/sprint_1_daywise_execution_plan.md)**: Squeezed 6-day breakdown of tasks, daily deliverables, and structured stand-up templates (June 17th – June 22nd).
*   📚 **[Learning Roadmap](file:///x:/CODING/PROJECTS/InternshipWork/Bluestock/ProjectNifty/planning/sprint_1_learning_roadmap.md)**: Day-by-day learning milestones covering Pandas, SQLite, pytest, and database validation.
*   📦 **[Deliverables & Presentation Guide](file:///x:/CODING/PROJECTS/InternshipWork/Bluestock/ProjectNifty/planning/sprint_1_deliverables_and_presentation.md)**: Complete list of files to build, datasets to upload, verification criteria, and guidelines on how to show/demo your work.

---

## 3. High-Level Project Timeline (Sprint 1)

| Date | Day | Phase / Focus | Key Deliverable |
| :--- | :--- | :--- | :--- |
| **June 17** | Day 1 | Scaffold & Environment Setup | `requirements.txt`, `.env.template`, project folders |
| **June 18** | Day 2 | Excel Loader & Normalisation | `loader.py`, `test_normalise.py` (20+ test cases) |
| **June 19** | Day 3 | Schema Validation & DB Setup | `validator.py`, `schema.sql`, `validation_failures.csv` |
| **June 20** | Day 4 | Supplementary Load & ETL Integration | `nifty100.db` (initial load), `load_audit.csv` |
| **June 21** | Day 5 | DQ Review & Debugging | Manual QA review checklist, Bug-free loader |
| **June 22** | Day 6 | SQL Analysis, Retrospective & Handoff | `exploratory_queries.sql`, `sprint1_retro.md`, v1.0 tag |

---

## 4. Key Reference Documents (from Master PDF)
- **Dataset Catalog**: Core datasets (Page 10–13), Supplementary datasets (Page 14–16)
- **System Architecture**: 7-Layer Data Platform (Page 18)
- **Data Quality Rules**: 16 Validation Rules (Page 28)
- **Coding Standards**: PEP 8, Black, Ruff, and testing conventions (Page 37)
- **Acceptance Criteria**: 20 Non-Negotiable Quality Gates (Page 32)
