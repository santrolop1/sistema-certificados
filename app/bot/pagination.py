from dataclasses import dataclass, field
from typing import Any

POR_PAGINA = 3
_KEY = "busqueda_paginada"


@dataclass
class Pagina:
    ids: list[int] = field(default_factory=list)      # IDs de certificados encontrados
    pagina: int = 0
    por_pagina: int = POR_PAGINA
    filtros: dict[str, Any] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.ids)

    @property
    def total_paginas(self) -> int:
        if not self.ids:
            return 0
        return (self.total + self.por_pagina - 1) // self.por_pagina

    @property
    def ids_actuales(self) -> list[int]:
        inicio = self.pagina * self.por_pagina
        return self.ids[inicio : inicio + self.por_pagina]

    @property
    def hay_anterior(self) -> bool:
        return self.pagina > 0

    @property
    def hay_siguiente(self) -> bool:
        return self.pagina < self.total_paginas - 1

    def avanzar(self) -> None:
        if self.hay_siguiente:
            self.pagina += 1

    def retroceder(self) -> None:
        if self.hay_anterior:
            self.pagina -= 1


def guardar_pagina(context, pagina: Pagina) -> None:
    context.user_data[_KEY] = pagina


def obtener_pagina(context) -> Pagina | None:
    return context.user_data.get(_KEY)


def limpiar_pagina(context) -> None:
    context.user_data.pop(_KEY, None)
