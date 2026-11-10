from __future__ import annotations


class AdaptadorConsentimientoDegradado:

    def guardar(
        self,
        identificador_sujeto: str,
        correo: str,
        decision: str,
        edad: int | None = None,
    ) -> None:
        pass

    def consultar(self, identificador_sujeto: str, correo: str = "") -> dict | None:
        return None
