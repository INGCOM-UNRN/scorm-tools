"""Integraciones del ecosistema (re-exporta los módulos eco_*, partidos por integración)."""

from .eco_deckard import (  # noqa: F401
    deckard_to_scorm,
)
from .eco_gift import (  # noqa: F401
    parse_gift_questions,
    gift_to_scorm_sco,
)
from .eco_diagramas import (  # noqa: F401
    _to_bishop_snapshot,
    generate_memory_diagram,
)
from .eco_auditoria import (  # noqa: F401
    _obtener_catalogo_kaneda,
    _obtener_catalogo_spunkmeyer,
    extract_and_audit_c_code,
    parse_scorm_tracking_log,
)
from .eco_idkfa import (  # noqa: F401
    parse_idkfa_template,
    idkfa_to_scorm_tracing,
)
from .eco_wasm import (  # noqa: F401
    scaffold_wasm_playground,
)
