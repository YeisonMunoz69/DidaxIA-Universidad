"""Emisión NDJSON del trabajo real, conservando el resultado de los reintentos."""

import asyncio
import json
import logging

from fastapi.responses import StreamingResponse

from adaptadores.entrantes.http.turno import fase_al_iniciar

_EN_CURSO = set()
_REGISTRO = logging.getLogger(__name__)


class EmisionDelTurno:
    def __init__(self, ejecutar, recordar, liberar):
        self.bucle = asyncio.get_running_loop()
        self.cola = asyncio.Queue()
        self.lineas = []
        self.ejecutar = ejecutar
        self.recordar = recordar
        self.liberar = liberar
        self.tarea = asyncio.create_task(self._resolver())
        # Desconectar el navegador no cancela un turno ni permite contarlo otra vez.
        _EN_CURSO.add(self.tarea)
        self.tarea.add_done_callback(_EN_CURSO.discard)

    def al_iniciar(self, nombre):
        fase = fase_al_iniciar(nombre)
        if fase is not None:
            linea = (json.dumps({"fase": fase.fase, "texto": fase.texto}, ensure_ascii=False) + "\n").encode()
            self.bucle.call_soon_threadsafe(self._emitir, linea)

    def _emitir(self, linea):
        if self.lineas and self.lineas[-1] == linea:
            return
        self.lineas.append(linea)
        self.cola.put_nowait(linea)

    async def _resolver(self):
        try:
            completadas = await self.ejecutar(self.al_iniciar)
            hubo_progreso = bool(self.lineas)
            for linea in completadas:
                if not hubo_progreso or "fase" not in json.loads(linea):
                    self._emitir(linea)
        except Exception as exc:  # noqa: BLE001 — no se expone una excepción interna al estudiante
            _REGISTRO.error("Fallo interno en la emisión del turno: %s", type(exc).__name__)
            ultima = next((json.loads(linea).get("fase", "") for linea in reversed(self.lineas)
                           if "fase" in json.loads(linea)), "")
            self._emitir((json.dumps({"degradado": {
                "situacion": "degradado", "ultima_fase": ultima, "turno": "",
                "explicacion": "No pudimos completar tu consulta en este momento.",
            }}, ensure_ascii=False) + "\n").encode())
        finally:
            try:
                self.recordar(tuple(self.lineas))
            finally:
                self.liberar()
                self.cola.put_nowait(None)

    async def lineas_en_vivo(self):
        while (linea := await self.cola.get()) is not None:
            yield linea

    def respuesta(self):
        return StreamingResponse(self.lineas_en_vivo(), media_type="application/x-ndjson",
                                 headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})
