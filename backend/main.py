import os
import sys
from typing import List
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# --- Path Configurations ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURRENT_DIR)
MODEL_SRC_DIR = os.path.join(BASE_DIR, "model", "ChangeFormer", "src")
RUNS_DATA_DIR = os.path.join(BASE_DIR, "runs")
FRONTEND_DIST_DIR = os.path.join(BASE_DIR, "frontend", "dist")

if MODEL_SRC_DIR not in sys.path:
    sys.path.append(MODEL_SRC_DIR)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from pipeline import ChangeDetectionPipeline
from visualizer import generate_rgb_preview, generate_mask_overlay, generate_triptych_preview, encode_image_to_base64
from fusion.evidence_fusion import EvidenceFusionEngine
from services.qwen_service import QwenMultimodalReasoningService

# --- Initialize FastAPI Application ---
app = FastAPI(
    title="GeoSentinel-AI API",
    description="Automated Sentinel-2 Change Detection Engine with Siamese ViT, Multi-Agent Swarm & Multimodal Qwen Dossier",
    version="1.0.0"
)

# Enable CORS for React frontend & public tunneling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Singletons initialized on startup
pipeline_instance = None
fusion_engine = None
qwen_service = None

@app.on_event("startup")
def startup_event():
    global pipeline_instance, fusion_engine, qwen_service
    print("[API Startup] Initializing Earth Engine & Siamese ViT pipeline...")
    pipeline_instance = ChangeDetectionPipeline(project_id="geosentinel-ai-511016")
    print("[API Startup] Initializing Multi-Agent Evidence Fusion Engine...")
    fusion_engine = EvidenceFusionEngine()
    print("[API Startup] Initializing Multimodal Qwen Dossier Engine...")
    qwen_service = QwenMultimodalReasoningService()
    print("[API Startup] GeoSentinel-AI Engine ready for inference and evidence swarms.")


# --- Request Schema ---
class DetectionRequest(BaseModel):
    bbox: List[float] = Field(
        ..., 
        description="Bounding box [min_lon, min_lat, max_lon, max_lat]",
        example=[76.150, 11.510, 76.180, 11.540]
    )
    pre_start: str = Field(..., example="2024-02-01")
    pre_end: str = Field(..., example="2024-04-15")
    post_start: str = Field(..., example="2024-12-01")
    post_end: str = Field(..., example="2025-01-30")
    threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    include_agent_swarm: bool = Field(default=True)
    generate_dossier: bool = Field(default=True)


# --- Core API Endpoints ---
@app.get("/api/health")
def health_check():
    return {
        "status": "ONLINE",
        "service": "GeoSentinel-AI Backend",
        "engine": "ChangeFormer ViT (in_chans=4)",
        "agent_swarm": "6-Agent Evidence Fusion Layer Active",
        "reasoning_engine": "Qwen Multimodal Dossier Active",
        "gee_project": "geosentinel-ai-511016"
    }


@app.post("/api/detect-change")
def detect_change(payload: DetectionRequest, request: Request):
    global pipeline_instance, fusion_engine, qwen_service
    if pipeline_instance is None or fusion_engine is None or qwen_service is None:
        raise HTTPException(status_code=503, detail="Engines not fully initialized.")

    if len(payload.bbox) != 4:
        raise HTTPException(status_code=422, detail="bbox must contain exactly 4 coordinates: [min_lon, min_lat, max_lon, max_lat]")

    try:
        # 1. Execute end-to-end ingestion and ViT inference
        result = pipeline_instance.run(
            bbox=payload.bbox,
            pre_range=(payload.pre_start, payload.pre_end),
            post_range=(payload.post_start, payload.post_end),
            base_output_dir=RUNS_DATA_DIR,
            threshold=payload.threshold
        )

        job_id = result["job_id"]
        job_dir = os.path.join(RUNS_DATA_DIR, job_id)

        # 2. Generate web-viewable PNG previews
        pre_png_name = "pre_preview.png"
        post_png_name = "post_preview.png"
        mask_png_name = "change_overlay.png"
        triptych_png_name = "triptych_preview.png"

        pre_png_path = os.path.join(job_dir, pre_png_name)
        post_png_path = os.path.join(job_dir, post_png_name)
        mask_png_path = os.path.join(job_dir, mask_png_name)
        triptych_png_path = os.path.join(job_dir, triptych_png_name)

        generate_rgb_preview(result["artifacts"]["pre_geotiff"], pre_png_path)
        generate_rgb_preview(result["artifacts"]["post_geotiff"], post_png_path)
        generate_mask_overlay(result["artifacts"]["mask_geotiff"], mask_png_path)
        generate_triptych_preview(pre_png_path, post_png_path, mask_png_path, triptych_png_path)

        base_url = str(request.base_url).rstrip("/")
        static_job_url = f"{base_url}/static/runs/{job_id}"

        result["web_previews"] = {
            "pre_rgb_url": f"{static_job_url}/{pre_png_name}",
            "post_rgb_url": f"{static_job_url}/{post_png_name}",
            "mask_overlay_url": f"{static_job_url}/{mask_png_name}",
            "triptych_url": f"{static_job_url}/{triptych_png_name}"
        }

        # 3. Execute Multi-Agent Swarm and Multimodal Dossier Generation
        if payload.include_agent_swarm:
            print(f"[API] Dispatching Multi-Agent Evidence Swarm for job: {job_id}...")
            fused_dossier = fusion_engine.fuse_evidence(
                bbox=payload.bbox,
                pre_geotiff=result["artifacts"]["pre_geotiff"],
                post_geotiff=result["artifacts"]["post_geotiff"],
                mask_geotiff=result["artifacts"]["mask_geotiff"],
                pre_date=result["metadata"]["pre_acquisition_date"],
                post_date=result["metadata"]["post_acquisition_date"],
                analytics=result["analytics"]
            )
            result["evidence_dossier"] = fused_dossier

            if payload.generate_dossier:
                print(f"[API] Synthesizing Multimodal Disaster Dossier for job: {job_id}...")
                b64_img = encode_image_to_base64(triptych_png_path)
                dossier_model = qwen_service.generate_dossier(
                    detection=result,
                    evidence=fused_dossier,
                    triptych_base64=b64_img
                )
                result["intelligence_dossier"] = dossier_model.model_dump()

        result["status"] = "COMPLETED"
        return result

    except Exception as e:
        print(f"[API Error] Pipeline processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Pipeline processing failed: {str(e)}")


# --- Static Artifact & SPA Route Handlers ---
os.makedirs(RUNS_DATA_DIR, exist_ok=True)

# 1. Dedicated Run Artifact Handler (Guarantees PNG/GeoTIFF delivery)
@app.get("/static/runs/{file_path:path}")
async def serve_run_artifacts(file_path: str):
    target_file = os.path.join(RUNS_DATA_DIR, file_path)
    if os.path.isfile(target_file):
        return FileResponse(target_file)
    raise HTTPException(status_code=404, detail="Artifact file not found")

# 2. Mount compiled React assets (JS & CSS bundles)
assets_dir = os.path.join(FRONTEND_DIST_DIR, "assets")
if os.path.exists(assets_dir):
    app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend_assets")

# 3. SPA Fallback for client routing (Never intercepts /api or /static)
@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("static/"):
        raise HTTPException(status_code=404, detail="Not Found")

    target_file = os.path.join(FRONTEND_DIST_DIR, full_path)
    if full_path and os.path.isfile(target_file):
        return FileResponse(target_file)

    index_file = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"message": "Frontend build not found. Please run npm run build."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)