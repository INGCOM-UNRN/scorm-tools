"""Integración con Bishop / Sebastian: diagramas de memoria."""

from __future__ import annotations

from pathlib import Path
from typing import Any




# ============================================================================
# 3. Integración con Bishop / Sebastian: Diagramas de Memoria
# ============================================================================

def _to_bishop_snapshot(
    stack_frames: list[dict[str, Any]],
    heap_blocks: list[dict[str, Any]] | None = None,
) -> Any:
    """Convierte estructuras crudas de stack/heap en SnapshotMemoria canónico de Bishop."""
    try:
        from bishop.core.models import BloqueHeap, SnapshotMemoria, StackFrameMemoria, VariableMemoria
    except ImportError:
        import sys
        sibling = Path(__file__).resolve().parents[4] / "bishop" / "src"
        if sibling.is_dir() and str(sibling) not in sys.path:
            sys.path.insert(0, str(sibling))
        try:
            from bishop.core.models import BloqueHeap, SnapshotMemoria, StackFrameMemoria, VariableMemoria
        except ImportError:
            return None

    frames_b: list[StackFrameMemoria] = []
    for idx, f in enumerate(stack_frames):
        fn_name = f.get("funcion") or f.get("function") or f"frame_{idx}"
        base = f.get("direccion_base") or f"0x7fff{idx:04x}"
        tope = f.get("direccion_tope") or f"0x7ffe{idx:04x}"
        vars_raw = f.get("variables", [])
        vars_b: list[VariableMemoria] = []

        if isinstance(vars_raw, list):
            for v in vars_raw:
                if isinstance(v, dict):
                    vars_b.append(VariableMemoria(
                        nombre=str(v.get("nombre") or v.get("name") or "var"),
                        tipo=str(v.get("tipo") or v.get("type") or "int"),
                        direccion=str(v.get("direccion") or v.get("address") or f"0x7fff{len(vars_b):02x}"),
                        valor=str(v.get("valor") or v.get("value") or "?"),
                        es_puntero=bool(v.get("es_puntero", "*" in str(v.get("tipo", "")))),
                        direccion_apuntada=v.get("direccion_apuntada") or v.get("target_address"),
                    ))
        elif isinstance(vars_raw, dict):
            for k, val in vars_raw.items():
                vars_b.append(VariableMemoria(
                    nombre=str(k),
                    tipo="int",
                    direccion=f"0x7fff{len(vars_b):02x}",
                    valor=str(val),
                ))

        frames_b.append(StackFrameMemoria(
            funcion=fn_name,
            direccion_base=base,
            direccion_tope=tope,
            variables=vars_b,
        ))

    heap_b: list[BloqueHeap] = []
    if heap_blocks:
        for j, b in enumerate(heap_blocks):
            addr = str(b.get("direccion") or b.get("address") or f"0xHEAP{j}")
            sz = int(b.get("tamanio_bytes") or b.get("size") or 16)
            liberado = bool(b.get("esta_liberado") or b.get("tag") == "liberado")
            contenido = str(b.get("contenido") or b.get("preview") or "...")
            heap_b.append(BloqueHeap(
                direccion=addr,
                tamanio_bytes=sz,
                esta_liberado=liberado,
                contenido=contenido,
            ))

    return SnapshotMemoria(
        archivo=Path("trace.json"),
        linea=1,
        frames=frames_b,
        heap=heap_b,
    )


def generate_memory_diagram(
    stack_frames: list[dict[str, Any]],
    heap_blocks: list[dict[str, Any]] | None = None,
) -> str:
    """Genera código Mermaid para visualizar memoria Stack y Heap dentro de lecciones SCORM compatible con Bishop/Sebastian."""
    # Soporte canónico delegando en visualizer de Bishop
    lines: list[str] = ["graph TD", "  subgraph Stack [Memoria Stack / Pila]"]

    for i, frame in enumerate(stack_frames):
        fn_name = frame.get("function") or frame.get("funcion") or f"frame_{i}"
        vars_raw = frame.get("variables", {})
        if isinstance(vars_raw, list):
            vars_str = "<br/>".join(
                f"{v.get('nombre', v.get('name', 'var'))}: {v.get('valor', v.get('value', '?'))}"
                for v in vars_raw if isinstance(v, dict)
            ) or "sin variables locales"
        elif isinstance(vars_raw, dict):
            vars_str = "<br/>".join(f"{k}: {v}" for k, v in vars_raw.items()) or "sin variables locales"
        else:
            vars_str = "sin variables locales"

        node_id = f"F_{i}"
        lines.append(f'    {node_id}["Frame: {fn_name}<br/>{vars_str}"]')

    for i in range(len(stack_frames) - 1):
        lines.append(f"    F_{i} -->|llama a| F_{i+1}")

    lines.append("  end")

    if heap_blocks:
        lines.append("  subgraph Heap [Memoria Heap / Dinámica]")
        for j, block in enumerate(heap_blocks):
            addr = block.get("address") or block.get("direccion") or f"0xHEAP{j}"
            bytes_sz = block.get("size") or block.get("tamanio_bytes") or 16
            tag = block.get("tag") or ("liberado" if block.get("esta_liberado") else "malloc")
            node_h = f"H_{j}"
            lines.append(f'    {node_h}["Bloque {addr}<br/>{bytes_sz} bytes ({tag})"]')
        lines.append("  end")

    return "\n".join(lines)
