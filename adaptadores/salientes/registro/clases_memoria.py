"""
clases_memoria.py — Clases y matrícula en memoria del proceso (`DD-12`)
=============================================================================

El respaldo de `AdaptadorClasesPostgres`: mismo `PuertoClases`
(`dominio/puertos/clases.py`), mismos modelos, sin base. `aplicacion.py`
construye uno u otro según `AGENTE_BD`, y `GET /api/salud` declara cuál cayó.

EL CODIGO DE CLASE NO ES UNA CREDENCIAL. Identifica una agrupación. Quién es
cada quien lo resuelve la autenticación de `DD-18`, que va aparte. Confundirlas
convertiría un código compartido por mensajería en una puerta abierta.

Regenerar el código NO expulsa a quien ya entró: invalida el código, no la
matrícula.

Dónde vivía antes, y por qué se movió
--------------------------------------------
Hasta la Fase 2 · sesión 3 esta clase vivía en
`adaptadores/entrantes/http/clases.py`, junto a los modelos que el adaptador
de PostgreSQL importaba desde ahí. Un almacén es un adaptador **saliente**:
tenerlo dentro del paquete HTTP obligaba a la composición a declarar el tipo
`Clases | AdaptadorClasesPostgres` —una unión que cruza las dos orillas— en
vez de un solo puerto. `adaptadores/entrantes/http/clases.py` conserva una
reexportación explícita para no romper a quien todavía importe de allí.

Nombres visibles en el respaldo de memoria
--------------------------------------------
PostgreSQL obtiene el nombre institucional de `persona`. Este respaldo no
tiene ese catálogo, por lo que `Matricula.como_fila()` conserva un rótulo
derivado cuando una prueba no le inyecta un nombre explícito. El rótulo es un
estado de dato ausente, no una identidad verificada.

🐛 **Corregido el 2026-08-22 · la matrícula se guardaba con la clave
equivocada.** Hasta esa fecha, `unirse()`/`mias()` se llamaban con
`datos["sesion"]` —el identificador de sesión efímero— y no con la
identidad estable. Cualquier cosa que rotara la sesión de quien ya se
había unido —«Nueva conversación», cerrar y volver a iniciar sesión, la
sesión expirando por su TTL— dejaba a esa persona matriculada bajo un
identificador que nadie iba a volver a presentar. La corrección es la
misma que `DD-27` ya aplicó en `rutas/turno.py`: la clave es
`sujeto_de(datos)`, resuelta en la RUTA y pasada a este almacén ya
resuelta; este archivo no conoce sesiones, sólo el identificador que le
llega.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""

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
    # Seis caracteres, mayúsculas y dígitos: se dicta por voz o se comparte por
    # mensajería sin ambigüedad de mayúscula/minúscula ni de "cero" y "o".
    alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alfabeto) for _ in range(6))


def _ahora() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Clases:
    """Almacén en memoria. Ver el docstring del módulo sobre por qué basta hoy."""

    def __init__(self) -> None:
        self._por_id: dict[str, Clase] = {}
        self._por_codigo: dict[str, str] = {}  # código -> id
        self._archivadas: set[str] = set()
        self._solicitudes: dict[str, SolicitudDeMatricula] = {}
        self._eventos: list[dict] = []
        self._historial: list[dict] = []
        self._contextos: dict[str, ContextoCurricular] = {}
        self._cerrojo = RLock()

    def crear(self, nombre: str, creador: str) -> Clase:
        identificador = secrets.token_urlsafe(8)
        codigo = _codigo()
        while codigo in self._por_codigo:  # colisión improbable, pero no imposible
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
        """Solo quien la creó puede regenerar. `None` si no existe o no es suya
        — la ambigüedad es deliberada: no distingue "no existe" de "no es tuya"
        hacia quien pregunta, para no confirmar la existencia de una clase ajena."""
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
        """Retira la clase de las vistas y conserva el objeto para auditoría."""
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
        """Las que creó, más las que se unió — `clases.js` pide una lista y no
        distingue rol: «del docente las suyas; del estudiante en las que está».

        `identificador` es `sujeto_de(datos)`, igual que en `unirse()`."""
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
        """`None` si no existe o `quien` no es su creador — la lista de
        matriculados es del docente que la creó, no de cualquiera."""
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
        """Equivalente en memoria; el rol se comprueba en el borde HTTP."""
        del investigador
        clase = self._por_id.get(identificador)
        return clase.matriculados.get(estudiante) if clase is not None else None

    def suprimir_sujeto(self, identificador: str) -> int:
        """RD-22: quita a `identificador` de la matrícula de toda clase donde
        esté —no borra las clases que haya creado, DD-12 no ofrece borrar una
        clase—. Devuelve cuántas matrículas quitó, para el recibo medido de
        `datos_personales.suprimir()`.

        Se llama a mano desde la ruta, igual que ya se hace con
        `sesiones.cerrar()` — ver `_ALCANZA_SIEMPRE` en `datos_personales.py`."""
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
