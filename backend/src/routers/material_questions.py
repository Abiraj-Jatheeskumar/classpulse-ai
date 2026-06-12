"""
AI question generation from uploaded lecture materials.

Two endpoints (instructor only):

  POST /api/questions/generate-from-material
      multipart upload -> parse slides/pages -> Azure OpenAI -> PREVIEW list
      (NOTHING is saved here; the instructor reviews first)

  POST /api/questions/bulk-create
      JSON list of (reviewed) questions -> saved via the SAME Question.create()
      used by manual creation, so they land in the identical question bank.
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from pydantic import BaseModel

from ..models.question import Question
from ..middleware.auth import require_instructor
from ..services.material_parser import parse_material
from ..services.azure_openai_service import azure_openai_service

router = APIRouter(prefix="/api/questions", tags=["questions-ai"])

MAX_FILE_BYTES = 20 * 1024 * 1024  # 20 MB
MAX_UNITS = 60                     # safety cap on slides/pages per upload
_AI_CONCURRENCY = 4                # parallel Azure calls


# ---------------------------------------------------------------------------
# Generate (preview only — not saved)
# ---------------------------------------------------------------------------
@router.post("/generate-from-material")
async def generate_from_material(
    file: UploadFile = File(...),
    count_per_unit: int = Form(1),
    mode: str = Form("difficulty"),        # "generic" | "difficulty" | "fixed_cluster"
    fixed_cluster: Optional[str] = Form(None),  # passive|moderate|active (mode=fixed_cluster)
    topic: Optional[str] = Form(None),
    course_id: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None),
    user: dict = Depends(require_instructor),
):
    if not azure_openai_service.is_enabled():
        raise HTTPException(
            status_code=503,
            detail="AI generation is not configured. Set AZURE_OPENAI_KEY and "
                   "AZURE_OPENAI_ENDPOINT, and ensure the 'openai' package is installed.",
        )

    count_per_unit = max(1, min(5, int(count_per_unit)))

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB).")

    try:
        unit_label, units = parse_material(file.filename, data)
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read the file: {e}")

    # Keep only units that actually have content, capped for safety.
    units = [(n, t) for (n, t) in units if (t or "").strip()][:MAX_UNITS]
    if not units:
        raise HTTPException(
            status_code=400,
            detail=f"No readable text found in the {unit_label}s of this file.",
        )

    topic_label = (topic or "").strip() or (file.filename or "Lecture")

    # Generate for all units with limited concurrency.
    sem = asyncio.Semaphore(_AI_CONCURRENCY)

    async def gen(unit_number: int, text: str):
        async with sem:
            return await azure_openai_service.generate_questions_for_slide(
                slide_text=text,
                slide_number=unit_number,
                count=count_per_unit,
                topic=topic_label,
            )

    results = await asyncio.gather(*[gen(n, t) for (n, t) in units])

    # Flatten + attach the chosen targeting so the frontend can show it.
    preview: List[Dict[str, Any]] = []
    for generated in results:
        for q in generated:
            qtype, target = _resolve_targeting(mode, fixed_cluster, q.get("suggestedCluster"))
            preview.append({
                "question": q["question"],
                "options": q["options"],
                "correctAnswer": q["correctAnswer"],
                "category": topic_label,
                "difficulty": q["difficulty"],
                "explanation": q.get("explanation", ""),
                "sourceSlide": q["sourceSlide"],
                "unitLabel": unit_label,
                "questionType": qtype,
                "targetCluster": target,
                "timeLimit": 30,
                "tags": ["ai-generated", f"{unit_label}-{q['sourceSlide']}"],
            })

    return {
        "success": True,
        "unitLabel": unit_label,
        "unitsProcessed": len(units),
        "generatedCount": len(preview),
        "topic": topic_label,
        "courseId": course_id,
        "sessionId": session_id,
        "questions": preview,
    }


def _resolve_targeting(mode: str, fixed_cluster: Optional[str], suggested: Optional[str]):
    """Decide questionType + targetCluster for a generated question."""
    valid_clusters = {"passive", "moderate", "active"}
    if mode == "generic":
        return "generic", None
    if mode == "fixed_cluster":
        fc = (fixed_cluster or "").lower()
        if fc in valid_clusters:
            return "cluster", fc
        return "generic", None
    # mode == "difficulty" (default): use AI's suggested cluster
    sc = (suggested or "").lower()
    if sc in valid_clusters:
        return "cluster", sc
    return "generic", None


# ---------------------------------------------------------------------------
# Bulk save (after instructor review)
# ---------------------------------------------------------------------------
class BulkQuestion(BaseModel):
    question: str
    options: List[str]
    correctAnswer: int
    category: str = "Lecture"
    tags: Optional[List[str]] = []
    timeLimit: Optional[int] = 30
    questionType: Optional[str] = "generic"        # "generic" | "cluster"
    targetCluster: Optional[str] = None            # passive|moderate|active
    courseId: Optional[str] = None
    sessionId: Optional[str] = None


class BulkCreateRequest(BaseModel):
    questions: List[BulkQuestion]


@router.post("/bulk-create")
async def bulk_create(
    payload: BulkCreateRequest,
    user: dict = Depends(require_instructor),
):
    if not payload.questions:
        raise HTTPException(status_code=400, detail="No questions provided.")

    instructor_id = user.get("id", "")
    created_ids: List[str] = []
    failed = 0

    for q in payload.questions:
        if not q.question.strip() or len(q.options) != 4:
            failed += 1
            continue
        qtype = q.questionType if q.questionType in ("generic", "cluster") else "generic"
        target = (q.targetCluster or "").lower() if qtype == "cluster" else None

        doc: Dict[str, Any] = {
            "question": q.question.strip(),
            "options": [str(o).strip() for o in q.options],
            "correctAnswer": int(q.correctAnswer),
            # IMPORTANT: for cluster questions, store the cluster name in
            # `category` too so the existing delivery logic matches it.
            "category": target if (qtype == "cluster" and target) else q.category,
            "topicCategory": q.category,
            "tags": q.tags or ["ai-generated"],
            "timeLimit": int(q.timeLimit or 30),
            "questionType": qtype,
            "targetCluster": target,
            "createdAt": datetime.now().isoformat(),
            "createdBy": instructor_id,
            "createdByEmail": user.get("email", ""),
            "instructorId": instructor_id,
            "source": "ai-generated",
        }
        if q.courseId:
            doc["courseId"] = q.courseId
        if q.sessionId:
            doc["sessionId"] = q.sessionId

        try:
            created = await Question.create(doc)
            created_ids.append(created.get("id", ""))
        except Exception as e:
            print(f"⚠️ bulk_create: failed to save a question: {e}")
            failed += 1

    return {
        "success": True,
        "savedCount": len(created_ids),
        "failedCount": failed,
        "ids": created_ids,
    }
