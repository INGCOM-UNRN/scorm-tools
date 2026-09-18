"""Lectura de bancos GIFT para el cuestionario SCORM autoevaluable (`from-gift`).

Interpreta los tipos que el cuestionario sabe corregir: opción múltiple, verdadero/falso,
respuesta corta y numérica. Todo lo demás (emparejamiento, ensayo, respuestas incrustadas,
descripciones) se informa en `omitidas` con su motivo: antes se descartaba en silencio y un
banco de cuatro preguntas terminaba con dos, sin ningún aviso.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

_DEL_ESCAPE = re.compile(r"\\([{}=~#:%\\])")


@dataclass
class ResultadoGift:
    preguntas: List[Dict[str, Any]] = field(default_factory=list)
    omitidas: List[Dict[str, str]] = field(default_factory=list)


def _quitar_escapes(texto: str) -> str:
    return _DEL_ESCAPE.sub(r"\1", texto).strip()


def _bloques(gift_text: str) -> List[str]:
    """Separa el banco en preguntas: una línea vacía corta el bloque solo si las llaves cierran."""
    bloques: List[str] = []
    actual: List[str] = []
    profundidad = 0
    for linea in gift_text.splitlines():
        if linea.strip().startswith("//"):
            continue
        if not linea.strip() and profundidad <= 0:
            if actual:
                bloques.append("\n".join(actual).strip())
                actual = []
            continue
        actual.append(linea)
        profundidad += _delta_llaves(linea)
    if actual:
        bloques.append("\n".join(actual).strip())
    return [b for b in bloques if b]


def _delta_llaves(texto: str) -> int:
    delta, escapado = 0, False
    for ch in texto:
        if escapado:
            escapado = False
        elif ch == "\\":
            escapado = True
        elif ch == "{":
            delta += 1
        elif ch == "}":
            delta -= 1
    return delta


def _grupos_de_llaves(texto: str) -> List[Tuple[int, int]]:
    """Posiciones (abre, cierra) de los grupos `{...}` de primer nivel, ignorando los escapados."""
    grupos: List[Tuple[int, int]] = []
    profundidad, inicio, escapado = 0, -1, False
    for i, ch in enumerate(texto):
        if escapado:
            escapado = False
        elif ch == "\\":
            escapado = True
        elif ch == "{":
            if profundidad == 0:
                inicio = i
            profundidad += 1
        elif ch == "}" and profundidad > 0:
            profundidad -= 1
            if profundidad == 0:
                grupos.append((inicio, i))
    return grupos


def _partir_sin_escapar(texto: str, separadores: str) -> List[Tuple[str, str]]:
    """Trocea por marcadores no escapados; devuelve [(marcador, contenido)] (el primero, sin marcador, va con '')."""
    partes: List[Tuple[str, str]] = []
    marcador, buffer, escapado = "", [], False
    for ch in texto:
        if escapado:
            buffer.append(ch)
            escapado = False
        elif ch == "\\":
            buffer.append(ch)
            escapado = True
        elif ch in separadores:
            partes.append((marcador, "".join(buffer)))
            marcador, buffer = ch, []
        else:
            buffer.append(ch)
    partes.append((marcador, "".join(buffer)))
    return partes


def _separar_retroalimentacion(texto: str) -> Tuple[str, str]:
    """`respuesta # comentario` -> (respuesta, comentario), respetando `\\#`."""
    partes = _partir_sin_escapar(texto, "#")
    cuerpo = partes[0][1]
    comentario = " ".join(c for _, c in partes[1:])
    return _quitar_escapes(cuerpo), _quitar_escapes(comentario)


def _numero(texto: str) -> Optional[float]:
    try:
        return float(texto.strip().replace(",", "."))
    except ValueError:
        return None


def _interpretar_numerica(cuerpo: str) -> Optional[List[Dict[str, float]]]:
    """`#4`, `#4:0.5`, `#1..3` o varias alternativas `#=1.5:0.1 =2`."""
    respuestas: List[Dict[str, float]] = []
    for _, item in _partir_sin_escapar(cuerpo.lstrip("#").strip() or "", "="):
        item = _separar_retroalimentacion(item)[0]
        if not item:
            continue
        if ".." in item:
            minimo, _, maximo = item.partition("..")
            a, b = _numero(minimo), _numero(maximo)
            if a is None or b is None:
                return None
            respuestas.append({"min": min(a, b), "max": max(a, b)})
            continue
        valor, _, tolerancia = item.partition(":")
        v = _numero(valor)
        t = _numero(tolerancia) if tolerancia else 0.0
        if v is None or t is None:
            return None
        respuestas.append({"value": v, "tolerance": abs(t)})
    return respuestas or None


_VERDADERO_FALSO = re.compile(r"^(T|F|TRUE|FALSE)\s*(?:#\s*(?P<uno>[^#].*?))?\s*(?:####\s*(?P<general>.*))?$", re.I | re.S)


def _interpretar_respuestas(prompt: str, titulo: str, cuerpo: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """Devuelve (pregunta, motivo_de_omision)."""
    crudo = cuerpo.strip()
    if not crudo:
        return None, "pregunta de ensayo (sin respuesta que corregir)"
    if "->" in crudo:
        return None, "emparejamiento (no soportado por el cuestionario)"

    m = _VERDADERO_FALSO.match(crudo)
    if m:
        pregunta = {
            "title": titulo or "Verdadero o Falso",
            "prompt": prompt,
            "type": "true_false",
            "correct": m.group(1).upper() in ("T", "TRUE"),
        }
        comentario = m.group("uno") or m.group("general")
        if comentario:
            pregunta["feedback"] = _quitar_escapes(comentario)
        return pregunta, ""

    if crudo.startswith("#"):
        respuestas = _interpretar_numerica(crudo)
        if respuestas is None:
            return None, "respuesta numérica que no se pudo interpretar"
        return {"title": titulo or "Numérica", "prompt": prompt, "type": "numeric", "answers": respuestas}, ""

    opciones = []
    for marcador, texto in _partir_sin_escapar(crudo, "=~"):
        if not marcador:
            continue
        texto = re.sub(r"^\s*%-?\d+(?:\.\d+)?%", "", texto)  # el crédito parcial no se modela
        respuesta, comentario = _separar_retroalimentacion(texto)
        if not respuesta:
            continue
        opcion = {"text": respuesta, "correct": marcador == "="}
        if comentario:
            opcion["feedback"] = comentario
        opciones.append(opcion)
    if not opciones:
        return None, "respuestas que no se pudieron interpretar"
    if all(o["correct"] for o in opciones):
        return {
            "title": titulo or "Respuesta corta",
            "prompt": prompt,
            "type": "short_answer",
            "answers": [o["text"] for o in opciones],
        }, ""
    return {"title": titulo or "Opción Múltiple", "prompt": prompt, "type": "multiple_choice", "options": opciones}, ""


def parsear_gift(gift_text: str) -> ResultadoGift:
    resultado = ResultadoGift()
    for bloque in _bloques(gift_text):
        if bloque.lstrip().upper().startswith("$CATEGORY"):
            continue  # directiva del banco, no una pregunta

        titulo = ""
        m_titulo = re.match(r"^::(.*?)::(.*)$", bloque, re.S)
        resto = bloque
        if m_titulo:
            titulo = _quitar_escapes(m_titulo.group(1))
            resto = m_titulo.group(2).strip()
        etiqueta = titulo or resto[:40].replace("\n", " ")

        grupos = _grupos_de_llaves(resto)
        if not grupos:
            resultado.omitidas.append({"titulo": etiqueta, "motivo": "sin bloque de respuestas { }: es una descripción"})
            continue
        if len(grupos) > 1:
            resultado.omitidas.append({
                "titulo": etiqueta,
                "motivo": f"{len(grupos)} respuestas incrustadas en el enunciado (cloze), no soportadas por el cuestionario",
            })
            continue

        abre, cierra = grupos[0]
        prompt = _quitar_escapes((resto[:abre] + " " + resto[cierra + 1:]).strip())
        pregunta, motivo = _interpretar_respuestas(prompt, titulo, resto[abre + 1:cierra])
        if pregunta is None:
            resultado.omitidas.append({"titulo": etiqueta, "motivo": motivo})
        else:
            resultado.preguntas.append(pregunta)
    return resultado
