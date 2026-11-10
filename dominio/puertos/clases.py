"""
clases.py — Contrato de clases y matrícula (`DD-12`)
=========================================================

Los dos modelos y el puerto que comparten las **dos** implementaciones del
almacén de clases: la de memoria del proceso
(`adaptadores/salientes/registro/clases_memoria.py`) y la de PostgreSQL
(`adaptadores/salientes/registro/clases_db.py`).

Por qué el contrato vive aquí y no en el adaptador entrante
------------------------------------------------------------------
Hasta la Fase 2 · sesión 3, `Clase` y `Matricula` se definían dentro de
`adaptadores/entrantes/http/clases.py` y el adaptador de PostgreSQL los
**importaba desde ahí**: un adaptador saliente dependía de uno entrante, que
es justo la dirección que `ADR-001` §7.2 prohíbe. El motivo declarado en su
día —«no hay un `dominio/modelo/clase.py`, y duplicarlos sería peor»— era
correcto en el diagnóstico y equivocado en el remedio: la salida no era
duplicar ni importar hacia atrás, sino tener **un** sitio neutral del que
dependan los dos lados.

Este módulo no importa FastAPI, ni Psycopg, ni lee variables de entorno.
`pruebas/arquitectura/test_reglas_arquitectonicas.py` lo comprueba para todo
`dominio/`.

Qué NO decide este puerto
-------------------------------
**No genera el código de clase.** El alfabeto y la longitud son de cada
adaptador; la colisión se resuelve donde está la garantía de unicidad —un
`dict` en memoria, un `UNIQUE` en la base—.

**No amplía la frontera académica de `DD-12`.** Sigue sin tareas,
calificaciones, entregas, calendario ni mensajería. `EQ-033` sí amplió el
contrato de matrícula: solicitar, consultar y resolver son operaciones de
producto aprobadas y por eso aparecen explícitamente en el puerto.


"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class ConflictoDeMatricula(ValueError):
    """La petición no corresponde al estado vigente de la matrícula."""


@dataclass(frozen=True)
class ContextoCurricular:
    """Referencia pedagógica vigente de una clase, nunca de una persona."""

    clase: str
    unidad: str = ""
    notacion: str = "sen"
    observaciones: str = ""
    actualizado_en: str | None = None

    def como_json(self) -> dict:
        return {
            "clase": self.clase,
            "unidad": self.unidad,
            "notacion": self.notacion,
            "observaciones": self.observaciones,
            "actualizado_en": self.actualizado_en,
        }


@dataclass(frozen=True)
class SolicitudDeMatricula:
    identificador: str
    estudiante: str
    clase_destino: str
    nombre_destino: str
    clase_origen: str | None
    nombre_origen: str | None
    clase_actual: str | None
    nombre_actual: str | None
    estado: str
    creada_en: str
    resuelta_en: str | None = None
    resuelta_por: str | None = None
    nombre_estudiante: str = ""
    correo_docente: str = ""
    nombre_docente: str = ""
    facultad_estudiante: str = ""
    programa_estudiante: str = ""
    semestre_estudiante: int | None = None
    docente: str = ""

    def como_elemento(self) -> dict:
        def referencia(identificador, nombre):
            return {"id": identificador, "nombre": nombre} if identificador else None

        elemento = {
            "id": self.identificador,
            "estudiante": self.estudiante,
            "nombre_estudiante": self.nombre_estudiante.strip(),
            "clase_destino": referencia(self.clase_destino, self.nombre_destino),
            "clase_origen": referencia(self.clase_origen, self.nombre_origen),
            "clase_actual": referencia(self.clase_actual, self.nombre_actual),
            "estado": self.estado,
            "creada_en": self.creada_en,
            "resuelta_en": self.resuelta_en,
            "resuelta_por": self.resuelta_por,
        }
        if self.facultad_estudiante or self.programa_estudiante or self.semestre_estudiante:
            elemento["perfil_estudiante"] = {
                "facultad": self.facultad_estudiante.strip(),
                "programa": self.programa_estudiante.strip(),
                "semestre": self.semestre_estudiante,
            }
        return elemento


@dataclass
class Matricula:
    """Quién está en la clase, y desde cuándo. Nada de progreso ni de indicios
    — `MisClases.svelte` ya lo declara: «no es un panel de seguimiento»."""

    identificador: str
    desde: str
    nombre: str = ""
    foto_referencia: str = ""
    facultad: str = ""
    programa: str = ""
    semestre: int | None = None

    def como_fila(self) -> dict:
        return {
            "identificador": self.identificador,
            "nombre": self.nombre.strip() or f"Estudiante {self.identificador[:8]}",
            "desde": self.desde,
            "tiene_foto": bool(self.foto_referencia),
            "facultad": self.facultad.strip(),
            "programa": self.programa.strip(),
            "semestre": self.semestre,
        }


@dataclass
class Clase:
    identificador: str
    nombre: str
    creador: str
    codigo: str
    matriculados: dict[str, Matricula] = field(default_factory=dict)

    def como_resumen(self) -> dict:
        return {
            "id": self.identificador,
            "nombre": self.nombre,
            "codigo": self.codigo,
            "integrantes": len(self.matriculados),
        }


@runtime_checkable
class PuertoClases(Protocol):
    """Lo que las rutas de `DD-12` consumen de verdad, y nada más.

    `obtener()` existe en las dos implementaciones y **no** está aquí: ninguna
    ruta lo llama. Se comprueba igual en la prueba de paridad entre memoria y
    PostgreSQL, que mira todos los métodos públicos compartidos; declararlo en
    el puerto lo convertiría en una obligación para cualquier implementación
    futura sin que ningún consumidor lo pida.
    """

    def crear(self, nombre: str, creador: str) -> Clase:
        """Una clase nueva con su código recién generado, sin matriculados."""
        ...

    def unirse(self, codigo: str, identificador: str) -> SolicitudDeMatricula | None:
        """Crea una solicitud pendiente; nunca matricula. Código desconocido: None.

        Una pendiente por estudiante; repetir su código devuelve la misma.
        Otra pendiente o una matrícula ya vigente en destino produce conflicto.
        La identidad es estable, resuelta por el servidor, nunca la sesión.
        """
        ...

    def solicitudes(self, quien: str, rol: str) -> list[SolicitudDeMatricula]:
        """Propias del estudiante, destinos propios del docente, todas del investigador.

        El rol lo resuelve el servidor; nunca procede del cuerpo HTTP.
        """
        ...

    def resolver_solicitud(
        self, identificador: str, quien: str, rol: str, decision: str
    ) -> SolicitudDeMatricula | None:
        """Aprobar/rechazar: docente de destino o investigador; cancelar: titular.

        None oculta solicitudes inexistentes o ajenas. Resolver una ya cerrada
        produce conflicto. Aprobar cambia la matrícula y registra sus periodos
        y auditoría en una transacción, sin atribuir clase a turnos históricos.
        """
        ...

    def regenerar_codigo(self, identificador: str, quien: str) -> str | None:
        """Solo quien la creó puede regenerar. `None` si no existe o no es
        suya — la ambigüedad es deliberada: no distingue los dos casos hacia
        quien pregunta, para no confirmar la existencia de una clase ajena.

        Invalida el código; **no** expulsa a quien ya entró.
        """
        ...

    def renombrar(self, identificador: str, quien: str, nombre: str) -> Clase | None:
        """Cambia el nombre de una clase propia; nunca su código ni integrantes.

        ``None`` no distingue clase inexistente de clase ajena.
        """
        ...

    def archivar(self, identificador: str, quien: str, motivo: str, rol: str = "docente") -> bool:
        """Docente propietario o investigador: cierra matrículas y conserva historia."""
        ...

    def mias(self, identificador: str) -> list[Clase]:
        """Las que creó, más las que se unió. `clases.js` pide una lista y no
        distingue rol."""
        ...

    def integrantes(self, identificador: str, quien: str) -> list[Matricula] | None:
        """`None` si no existe o `quien` no es su creador — la lista de
        matriculados es del docente que la creó, no de cualquiera."""
        ...

    def retirar_integrante(
        self, identificador: str, quien: str, estudiante: str, motivo: str
    ) -> Matricula | None:
        """Cierra una matrícula vigente de una clase propia y conserva su historia.

        ``None`` oculta por igual una clase inexistente, una clase ajena y una
        persona que ya no pertenece a ella. El motivo queda sólo en auditoría;
        retirar no borra la cuenta, sus conversaciones ni periodos históricos.
        """
        ...

    def contexto_curricular(self, identificador: str, quien: str) -> ContextoCurricular | None:
        """Contexto de una clase propia; ``None`` oculta clase inexistente o ajena."""
        ...

    def guardar_contexto_curricular(
        self, identificador: str, quien: str, unidad: str, notacion: str, observaciones: str
    ) -> ContextoCurricular | None:
        """Actualiza el contexto de una clase propia y devuelve su versión vigente."""
        ...

    def integrante_para_investigacion(
        self, identificador: str, investigador: str, estudiante: str
    ) -> Matricula | None:
        """Un integrante concreto para la ficha institucional auditada.

        La implementación PostgreSQL vuelve a exigir el rol investigador; el
        borde no se apoya sólo en ocultar un botón. ``None`` no distingue curso
        inexistente de estudiante ajeno a esa cohorte.
        """
        ...

    def suprimir_sujeto(self, identificador: str) -> int:
        """`RD-22`: quita a `identificador` de la matrícula de toda clase donde
        esté. No borra las clases que haya creado —`DD-12` no ofrece borrar una
        clase—. Devuelve cuántas matrículas quitó, para el recibo medido de
        `datos_personales.suprimir()`."""
        ...
