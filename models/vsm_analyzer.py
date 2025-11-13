# models/vsm_analyzer.py
from typing import Dict, List, Any
from .ai_engine import MLAnalyzer
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class VSMAnalyzer:
    def __init__(self, enable_ai: bool = True):
        self.enable_ai = enable_ai
        self.ml = MLAnalyzer() if enable_ai else None

    def _topological_sort(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Simple topological ordering heuristics:
        - If steps are given in order respecting dependencies, keep that order.
        - Otherwise, perform Kahn's algorithm to avoid cycles (best-effort).
        """
        name_map = {s["name"]: s for s in steps}
        deps_map = {s["name"]: set(s.get("depends_on", [])) for s in steps}
        # remove self-dependencies and unknowns
        for n in deps_map:
            deps_map[n] = set(d for d in deps_map[n] if d in name_map and d != n)

        # compute in-degree
        indeg = {n: 0 for n in name_map}
        for n, deps in deps_map.items():
            for d in deps:
                indeg[n] += 1

        # Kahn's algorithm
        queue = [n for n, d in indeg.items() if d == 0]
        ordered = []
        while queue:
            n = queue.pop(0)
            ordered.append(name_map[n])
            # remove edges
            for m, deps in deps_map.items():
                if n in deps:
                    deps.remove(n)
                    indeg[m] -= 1
                    if indeg[m] == 0:
                        queue.append(m)
        # If cycle (some nodes not in ordered), append remaining nodes
        remaining = [name_map[n] for n in name_map if name_map[n] not in ordered]
        return ordered + remaining

    def compute_dependency_flow(self, steps: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], float]:
        """
        Calcule wait_time / start / end pour chaque étape en considérant dépendances.
        Si une étape dépend de plusieurs parents, elle démarre après le parent le plus tardif
        (max end_time).
        """
        # copy to avoid mutating input
        steps_copy = [dict(s) for s in steps]
        name_index = {s["name"]: s for s in steps_copy}
        ordered = self._topological_sort(steps_copy)

        completion = {}  # end_time by name
        for s in ordered:
            deps = s.get("depends_on", []) or []
            # filter unknown deps
            deps = [d for d in deps if d in completion]
            if not deps:
                start = 0.0
            else:
                start = max(completion[d] for d in deps)
            cycle = float(s.get("cycle_time", 0.0))
            end = start + cycle
            s["wait_time"] = round(start, 2)   # waiting until start
            s["start_time"] = round(start, 2)
            s["end_time"] = round(end, 2)
            s["_predicted_wait"] = False
            completion[s["name"]] = end

        total_lead = max(completion.values()) if completion else 0.0
        return ordered, round(total_lead, 2)

    def analyze(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        steps_in = payload.get("steps", [])
        process_name = payload.get("process_name", "Processus non défini")
        # Ensure each step has required fields and a unique name
        validated = []
        seen = set()
        for s in steps_in:
            name = s.get("name")
            if not name:
                raise ValueError("Chaque étape doit avoir un nom unique.")
            if name in seen:
                raise ValueError(f"Nom d'étape dupliqué: {name}")
            seen.add(name)
            validated.append({
                "name": name,
                "cycle_time": float(s.get("cycle_time", 0.0)),
                "cost": float(s.get("cost", 0.0)),
                "value_added": bool(s.get("value_added", False)),
                "depends_on": s.get("depends_on", []) or []
            })

        # compute dependency-driven schedule
        ordered_steps, lead_time = self.compute_dependency_flow(validated)

        # If ML available: predict waits and detect critical steps
        alerts = []
        if self.enable_ai and self.ml:
            # predict waits and mark predicted if predicted > scheduled start (indicates buffer)
            for s in ordered_steps:
                pred_wait = self.ml.predict_wait_time(s)
                s["predicted_wait"] = pred_wait
                # if predicted_wait (model) > schedule start_time => indicates potential extra waiting
                if pred_wait > s["start_time"] + 0.001:
                    s["_predicted_wait"] = True
                    alerts.append(f"ML alert: {s['name']} predicted wait {pred_wait}h > scheduled start {s['start_time']}h")
            
            # ml-based critical flags
            flags = self.ml.predict_critical_flags(ordered_steps)
            for s, f in zip(ordered_steps, flags):
                if f == 1:
                    alerts.append(f"ML critical: {s['name']} (pred_wait={s.get('predicted_wait')}, cycle={s.get('cycle_time')})")

        # summary KPIs
        total_cycle = sum(s["cycle_time"] for s in ordered_steps)
        total_va = sum(s["cycle_time"] for s in ordered_steps if s["value_added"])
        va_ratio = round((total_va / lead_time * 100), 1) if lead_time > 0 else 0.0

        # timeline returned as list in scheduled order
        timeline = [{
            "name": s["name"],
            "start": s["start_time"],
            "end": s["end_time"],
            "wait": s["wait_time"],
            "cycle": s["cycle_time"],
            "value_added": s["value_added"],
            "predicted_wait": s.get("predicted_wait"),
            "predicted_flag": s.get("_predicted_wait", False)
        } for s in ordered_steps]

        # build report text (simple, local) - AVEC les alertes intégrées
        report_lines = [
            f"Rapport VSM - {process_name}",
            f"Lead time planifié: {lead_time} h",
            f"VA ratio: {va_ratio} %",
            "",
            "Alertes détectées:"
        ]
        if alerts:
            for a in alerts:
                report_lines.append(f"- {a}")
        else:
            report_lines.append("- Aucune alerte critique détectée selon le modèle local")

        report_lines.extend([
            "",
            "Recommandations:",
            "1) Vérifier les étapes marqué(es) ML alert / ML critical.",
            "2) Rééquilibrer la charge entre opérations en amont.",
            "3) Réduire stocks buffers identifiés."
        ])

        result = {
            "process": process_name,
            "summary": {
                "process": process_name,
                "lead_time": lead_time,
                "va_ratio": va_ratio,
                "total_cycle_time": round(total_cycle, 2),
                "total_wait_time": round(sum(s["wait_time"] for s in ordered_steps), 2),
                "nb_steps": len(ordered_steps)
            },
            "timeline": timeline,
            "alerts": [],  # Liste vide pour ne pas afficher en bas
            "ai_report": "\n".join(report_lines),  # Rapport AVEC les alertes intégrées
            "analysis_timestamp": datetime.utcnow().isoformat() + "Z",
            "steps": ordered_steps
        }
        return result