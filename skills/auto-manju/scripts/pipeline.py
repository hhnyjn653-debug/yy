#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except Exception as exc:
    raise SystemExit("Please install pyyaml: pip install pyyaml") from exc


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def qc_gate(report: Dict[str, Any], thresholds: Dict[str, float]) -> bool:
    c = report.get("character_consistency", 0)
    p = report.get("plot_consistency", 0)
    a = report.get("av_quality", 0)
    return c >= thresholds["character_consistency"] and p >= thresholds["plot_consistency"] and a >= thresholds["av_quality"]


class PlatformRouter:
    """根据能力需求和阶段，选择可调用的平台与模型。"""

    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg
        self.platforms = cfg.get("platforms", {})
        self.stage_plan = cfg.get("stage_plan", {})

    def route_stage(self, stage: str) -> Dict[str, Any]:
        stage_cfg = self.stage_plan.get(stage, {})
        capability = stage_cfg.get("capability")
        mode = stage_cfg.get("mode", "quality_first")
        allow = stage_cfg.get("allow", [])

        scored: List[Dict[str, Any]] = []
        for name in allow:
            p = self.platforms.get(name)
            if not p:
                continue
            caps = p.get("capabilities", [])
            if capability not in caps:
                continue
            latency = float(p.get("latency_score", 0.5))
            quality = float(p.get("quality_score", 0.5))
            cost = float(p.get("cost_score", 0.5))
            if mode == "quality_first":
                score = quality * 0.7 + latency * 0.1 + cost * 0.2
            elif mode == "speed_first":
                score = latency * 0.6 + quality * 0.3 + cost * 0.1
            else:  # balanced
                score = quality * 0.5 + latency * 0.25 + cost * 0.25
            scored.append({"platform": name, "score": round(score, 4), "config": p})

        scored.sort(key=lambda x: x["score"], reverse=True)
        primary = scored[0] if scored else None
        fallback = scored[1] if len(scored) > 1 else None

        return {
            "stage": stage,
            "capability": capability,
            "decision_mode": mode,
            "primary": primary["platform"] if primary else None,
            "fallback": fallback["platform"] if fallback else None,
            "candidates": [{"platform": x["platform"], "score": x["score"]} for x in scored],
            "call_guide": self._call_guide(stage, primary["config"] if primary else {}),
        }

    @staticmethod
    def _call_guide(stage: str, platform_cfg: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trigger": f"当 {stage} 阶段进入执行态且前置审核通过时调用",
            "api_base_env": platform_cfg.get("api_base_env", "SET_API_BASE"),
            "api_key_env": platform_cfg.get("api_key_env", "SET_API_KEY"),
            "model": platform_cfg.get("model", "replace_with_real_model"),
            "input_contract": platform_cfg.get("input_contract", "json"),
            "output_contract": platform_cfg.get("output_contract", "json"),
            "retry_policy": {"max_retries": 3, "backoff_sec": [1, 2, 4]},
        }


class LLMProvider:
    def generate_json(self, system_prompt: str, user_text: str, stage_route: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "mock": True,
            "route": stage_route,
            "prompt": system_prompt[:120],
            "summary": "Replace with real Responses/API call using route.primary platform.",
            "input_chars": len(user_text),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="novel text file")
    parser.add_argument("--config", required=True, help="config yaml")
    parser.add_argument("--outdir", required=True, help="output directory")
    args = parser.parse_args()

    novel_text = read_text(Path(args.input))
    cfg = load_yaml(Path(args.config))
    outdir = Path(args.outdir)

    skill_root = Path(__file__).resolve().parents[1]
    prompts = load_yaml(skill_root / "templates" / "prompts.yaml")

    router = PlatformRouter(cfg)
    llm = LLMProvider()

    routing_plan = {
        "story_insight": router.route_stage("story_insight"),
        "character_bible": router.route_stage("character_bible"),
        "script_generation": router.route_stage("script_generation"),
        "storyboard_generation": router.route_stage("storyboard_generation"),
        "video_generation": router.route_stage("video_generation"),
        "tts_generation": router.route_stage("tts_generation"),
        "music_generation": router.route_stage("music_generation"),
        "editing": router.route_stage("editing"),
        "qc": router.route_stage("qc"),
    }
    save_json(outdir / "00_routing_plan.json", routing_plan)

    save_json(outdir / "01_story_insight.json", llm.generate_json(prompts["story_insight"], novel_text, routing_plan["story_insight"]))
    save_json(outdir / "02_character_bible.json", llm.generate_json(prompts["character_bible"], novel_text, routing_plan["character_bible"]))
    save_json(outdir / "03_script.json", llm.generate_json(prompts["script_generation"], novel_text, routing_plan["script_generation"]))

    storyboard = {
        "mock": True,
        "route": routing_plan["storyboard_generation"],
        "note": "Replace with shot planning + selected video platform orchestration.",
        "shots": [],
    }
    save_json(outdir / "04_storyboard.json", storyboard)

    qc = {"character_consistency": 0.9, "plot_consistency": 0.88, "av_quality": 0.86, "issues": []}
    save_json(outdir / "07_qc_report.json", qc)

    passed = qc_gate(qc, cfg["thresholds"])
    save_json(outdir / "08_learning_log.json", {"run_passed": passed, "action": "publish" if passed else "regen"})

    final_video = outdir / "06_edit" / "final.mp4"
    final_video.parent.mkdir(parents=True, exist_ok=True)
    final_video.write_bytes(b"")

    print(json.dumps({"ok": True, "passed": passed, "outdir": str(outdir)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
