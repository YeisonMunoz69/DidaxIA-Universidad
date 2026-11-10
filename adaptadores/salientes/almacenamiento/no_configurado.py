from __future__ import annotations

from dominio.puertos.almacenamiento_privado import AlmacenamientoNoConfigurado


class AlmacenamientoNoConfiguradoAdaptador:

    def reservar(self, contenido: bytes, *, sujeto_google: str, intento: int) -> str:
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado: la carpeta, "
            "la credencial y la custodia siguen siendo una decisión del equipo"
        )

    def confirmar(self, referencia: str) -> None:
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado"
        )

    def retirar(self, referencia: str) -> bool:
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado"
        )

    def recuperar(self, referencia: str) -> bytes:
        raise AlmacenamientoNoConfigurado(
            "el almacenamiento privado de EQ-021 no está configurado: no hay "
            "de dónde recuperar la autorización del representante"
        )

    def pendientes(self) -> tuple[str, ...]:
        return ()

    def esta_configurado(self) -> bool:
        return False

    def estado_publicable(self) -> dict:
        return {
            "configurado": False,
            "tipo": "no_configurado",
            "disponible": False,
            "reservas_pendientes": 0,
        }
