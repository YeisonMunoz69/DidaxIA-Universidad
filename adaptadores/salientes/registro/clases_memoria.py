from __future__ import annotations

import secrets
from dataclasses import replace
from datetime import UTC, datetime
from threading import RLock

from dominio.puertos.clases import (
    Clase,
    ConflictoDeMatricula,
    ContextoCurricular,
    Matricula,
    SolicitudDeMatricula,
)


def _codigo() -> str:
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(6))

def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")

class Clases:

    def __init__(self) -> None:
        self._por_id: dict[str, Clase] = {}
        self._por_codigo: dict[str, str] = {}
        self._archivadas: set[str] = set()
        self._solicitudes: dict[str, SolicitudDeMatricula] = {}
        self._eventos: list[dict] = []
        self._historial: list[dict] = []
        self._contextos: dict[str, ContextoCurricular] = {}
        self._cerrojo = RLock()

    def crear(self, nombre: str, creador: str) -> Clase:
        identificador = secrets.token_urlsafe(8)
        codigo = _codigo()
        while codigo in self._por_codigo:
            codigo = _codigo()
        clase = Clase(identificador=identificador, nombre=nombre, creador=creador, codigo=codigo)
        self._por_id[identificador] = clase
        self._por_codigo[codigo] = identificador
        return clase

    def _actual(self, estudiante: str) -> Clase | None:
        return next((c for c in self._por_id.values()
                     if c.identificador not in self._archivadas
                     and estudiante in c.matriculados), None)

    def _con_actual(self, solicitud: SolicitudDeMatricula) -> SolicitudDeMatricula:
        actual = self._actual(solicitud.estudiante)
        return replace(
            solicitud, clase_actual=actual.identificador if actual else None,
            nombre_actual=actual.nombre if actual else None,
        )

    def unirse(self, codigo: str, identificador: str) -> SolicitudDeMatricula | None:
        with self._cerrojo:
            id_clase = self._por_codigo.get(codigo.strip().upper())
            if id_clase is None:
                return None
            actual = self._actual(identificador)
            if actual and actual.identificador == id_clase:
                raise ConflictoDeMatricula("ya tienes matrícula vigente en esta clase")
            pendiente = next((s for s in self._solicitudes.values()
                              if s.estudiante == identificador and s.estado == "pendiente"), None)
            if pendiente:
                if pendiente.clase_destino == id_clase:
                    return self._con_actual(pendiente)
                raise ConflictoDeMatricula("cancela tu solicitud pendiente antes de pedir otra clase")
            solicitud = SolicitudDeMatricula(
                identificador=secrets.token_urlsafe(12), estudiante=identificador,
                clase_destino=id_clase, nombre_destino=self._por_id[id_clase].nombre,
                clase_origen=actual.identificador if actual else None,
                nombre_origen=actual.nombre if actual else None,
                clase_actual=actual.identificador if actual else None,
                nombre_actual=actual.nombre if actual else None,
                estado="pendiente", creada_en=_ahora(),
                docente=self._por_id[id_clase].creador,
            )
            self._solicitudes[solicitud.identificador] = solicitud
            self._anotar(solicitud, identificador, "estudiante")
            return solicitud

    def solicitudes(self, quien: str, rol: str) -> list[SolicitudDeMatricula]:
        with self._cerrojo:
            return [self._con_actual(s) for s in self._solicitudes.values()
                    if self._visible(s, quien, rol)]

    def _visible(self, solicitud: SolicitudDeMatricula, quien: str, rol: str) -> bool:
        return (
            rol == "investigador"
            or (rol == "docente" and self._por_id[solicitud.clase_destino].creador == quien)
            or (rol == "estudiante" and solicitud.estudiante == quien)
        )

    def _anotar(self, solicitud: SolicitudDeMatricula, quien: str, rol: str) -> None:
        self._eventos.append({"solicitud": solicitud.identificador, "actor": quien,
                              "rol_actor": rol, "estado": solicitud.estado, "momento": _ahora()})

    def resolver_solicitud(
        self, identificador: str, quien: str, rol: str, decision: str
    ) -> SolicitudDeMatricula | None:
        with self._cerrojo:
            solicitud = self._solicitudes.get(identificador)
            if solicitud is None or not self._visible(solicitud, quien, rol):
                return None
            if decision == "cancelada":
                if rol != "estudiante" or solicitud.estudiante != quien:
                    return None
            elif decision not in {"aprobada", "rechazada"} or rol not in {"docente", "investigador"}:
                return None
            if solicitud.estado != "pendiente":
                raise ConflictoDeMatricula("esta solicitud ya fue resuelta")
            momento = _ahora()
            if decision == "aprobada":
                self._aprobar(solicitud, momento)
            resuelta = replace(solicitud, estado=decision, resuelta_en=momento, resuelta_por=quien)
            self._solicitudes[identificador] = resuelta
            self._anotar(resuelta, quien, rol)
            return self._con_actual(resuelta)

    def _aprobar(self, solicitud: SolicitudDeMatricula, momento: str) -> None:
        actual = self._actual(solicitud.estudiante)
        if (actual.identificador if actual else None) != solicitud.clase_origen:
            raise ConflictoDeMatricula("la matrícula cambió; cancela y crea una nueva solicitud")
        for periodo in self._historial:
            if periodo["estudiante"] == solicitud.estudiante and periodo["hasta"] is None:
                periodo["hasta"] = momento
        for clase in self._por_id.values():
            clase.matriculados.pop(solicitud.estudiante, None)
        self._por_id[solicitud.clase_destino].matriculados[solicitud.estudiante] = Matricula(
            identificador=solicitud.estudiante, desde=momento,
        )
        self._historial.append({"estudiante": solicitud.estudiante,
                                "clase": solicitud.clase_destino, "desde": momento,
                                "hasta": None, "solicitud": solicitud.identificador})

    def regenerar_codigo(self, identificador: str, quien: str) -> str | None:
        clase = self._por_id.get(identificador)
        if clase is None or clase.creador != quien or identificador in self._archivadas:
            return None
        del self._por_codigo[clase.codigo]
        clase.codigo = _codigo()
        while clase.codigo in self._por_codigo:
            clase.codigo = _codigo()
        self._por_codigo[clase.codigo] = identificador
        return clase.codigo

    def renombrar(self, identificador: str, quien: str, nombre: str) -> Clase | None:
        clase = self._por_id.get(identificador)
        if clase is None or clase.creador != quien or identificador in self._archivadas:
            return None
        clase.nombre = nombre
        return clase

    def archivar(self, identificador: str, quien: str, motivo: str, rol: str = "docente") -> bool:
        with self._cerrojo:
            clase = self._por_id.get(identificador)
            if (clase is None or identificador in self._archivadas
                    or rol not in {"docente", "investigador"}
                    or (rol == "docente" and clase.creador != quien)):
                return False
            self._archivadas.add(identificador)
            self._por_codigo.pop(clase.codigo, None)
            momento = _ahora()
            retirados = len(clase.matriculados)
            for periodo in self._historial:
                if periodo["clase"] == identificador and periodo["hasta"] is None:
                    periodo["hasta"] = momento
            clase.matriculados.clear()
            for clave, solicitud in list(self._solicitudes.items()):
                if (identificador in {solicitud.clase_destino, solicitud.clase_origen}
                        and solicitud.estado == "pendiente"):
                    cancelada = replace(solicitud, estado="cancelada",
                                        resuelta_en=momento, resuelta_por=quien)
                    self._solicitudes[clave] = cancelada
                    self._anotar(cancelada, quien, rol)
            self._eventos.append({"operacion": "clase.archivada", "actor": quien,
                                  "rol_actor": rol, "clase": identificador,
                                  "motivo": motivo, "momento": momento,
                                  "matriculas_cerradas": retirados})
            return True

    def mias(self, identificador: str) -> list[Clase]:
        creadas = [c for c in self._por_id.values()
                   if c.identificador not in self._archivadas and c.creador == identificador]
        unidas = [
            c for c in self._por_id.values()
            if c.identificador not in self._archivadas
            and c.creador != identificador and identificador in c.matriculados
        ]
        return creadas + unidas

    def obtener(self, identificador: str) -> Clase | None:
        return None if identificador in self._archivadas else self._por_id.get(identificador)

    def integrantes(self, identificador: str, quien: str) -> list[Matricula] | None:
        clase = self._por_id.get(identificador)
        if clase is None or clase.creador != quien or identificador in self._archivadas:
            return None
        return list(clase.matriculados.values())

    def retirar_integrante(
        self, identificador: str, quien: str, estudiante: str, motivo: str
    ) -> Matricula | None:
        with self._cerrojo:
            clase = self._por_id.get(identificador)
            if clase is None or clase.creador != quien:
                return None
            matricula = clase.matriculados.pop(estudiante, None)
            if matricula is None:
                return None
            momento = _ahora()
            for periodo in self._historial:
                if (
                    periodo["estudiante"] == estudiante
                    and periodo["clase"] == identificador
                    and periodo["hasta"] is None
                ):
                    periodo["hasta"] = momento
            self._eventos.append({
                "operacion": "matricula.retirada_por_docente",
                "actor": quien,
                "sujeto": estudiante,
                "clase": identificador,
                "motivo": motivo,
                "momento": momento,
            })
            return matricula

    def contexto_curricular(self, identificador: str, quien: str) -> ContextoCurricular | None:
        clase = self._por_id.get(identificador)
        if clase is None or clase.creador != quien:
            return None
        return self._contextos.get(identificador, ContextoCurricular(clase=identificador))

    def guardar_contexto_curricular(
        self, identificador: str, quien: str, unidad: str, notacion: str, observaciones: str
    ) -> ContextoCurricular | None:
        clase = self._por_id.get(identificador)
        if clase is None or clase.creador != quien:
            return None
        contexto = ContextoCurricular(
            clase=identificador,
            unidad=unidad,
            notacion=notacion,
            observaciones=observaciones,
            actualizado_en=_ahora(),
        )
        self._contextos[identificador] = contexto
        return contexto

    def integrante_para_investigacion(
        self, identificador: str, investigador: str, estudiante: str
    ) -> Matricula | None:

        del investigador
        clase = self._por_id.get(identificador)
        return clase.matriculados.get(estudiante) if clase is not None else None

    def suprimir_sujeto(self, identificador: str) -> int:
        quitadas = 0
        for clase in self._por_id.values():
            if clase.matriculados.pop(identificador, None) is not None:
                quitadas += 1
        propias = {s.identificador for s in self._solicitudes.values()
                   if s.estudiante == identificador}
        self._solicitudes = {k: s for k, s in self._solicitudes.items() if k not in propias}
        self._eventos = [e for e in self._eventos if e.get("solicitud") not in propias]
        self._historial = [h for h in self._historial if h["estudiante"] != identificador]
        return quitadas
