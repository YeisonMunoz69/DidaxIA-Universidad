from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.rutas.comun import mantenimiento
from dominio.modelo.acceso import AccesoCalculado, calcular_acceso, permite_tutoria_academica
from dominio.modelo.consentimiento import Alcance
from dominio.modelo.redecision import (
    AccionesDeDecision,
    DimensionDecidible,
    acciones_disponibles,
)
from dominio.puertos.almacen import AlmacenNoConfigurado, AlmacenNoDisponible

if TYPE_CHECKING:
    from dominio.modelo.acceso import EstadoVigente
    from dominio.puertos.almacenamiento_privado import PuertoAlmacenamientoPrivado
    from dominio.puertos.consentimiento_versionado import (
        PuertoEventosDeConsentimiento,
        PuertoVersionesDeConsentimiento,
    )
    from dominio.puertos.decision_conjunta import PuertoDecisionConjunta
    from dominio.puertos.estado_vigente import PuertoEstadoVigente
    from dominio.puertos.gobierno import PuertoNotificacion
    from dominio.puertos.identidad import PuertoIdentidad
    from dominio.puertos.instantaneas import PuertoInstantaneasDeConsentimiento
    from dominio.puertos.menores import (
        PuertoAsentimiento,
        PuertoEvidenciaDelRepresentante,
    )

@dataclass(frozen=True)
class Repositorios:

    identidades: PuertoIdentidad
    versiones: PuertoVersionesDeConsentimiento
    eventos: PuertoEventosDeConsentimiento
    asentimientos: PuertoAsentimiento
    evidencias: PuertoEvidenciaDelRepresentante
    estado_vigente: PuertoEstadoVigente
    almacenamiento: PuertoAlmacenamientoPrivado
    decision_conjunta: PuertoDecisionConjunta
    notificacion: PuertoNotificacion

    instantaneas: PuertoInstantaneasDeConsentimiento | None = None

def leer_estado(repos: Repositorios, sujeto: str):
    try:
        estado = repos.estado_vigente.estado_vigente(sujeto)
    except (AlmacenNoConfigurado, AlmacenNoDisponible):
        return None, None, mantenimiento("no se pudo leer el estado de consentimiento")
    if estado is None:

        return None, None, mantenimiento("la identidad de esta sesión no está disponible")
    return estado, calcular_acceso(estado), None

def recibo_de(evento, alcance: Alcance) -> dict:
    decision = getattr(evento, "decision", None) or evento.estado
    return {
        "secuencia": evento.secuencia,
        "momento": evento.momento.isoformat(),
        "version": evento.version,
        "alcance": alcance.value,
        "decision": decision.value,
        "huella": evento.comprobante,
    }

def dimensiones_decidibles(estado: EstadoVigente) -> tuple[DimensionDecidible, ...]:
    if estado.eliminacion_solicitada:

        return ()
    perfil = estado.perfil
    if perfil is None or perfil.edad is None:
        return ()
    dimensiones = [
        DimensionDecidible(
            alcance=Alcance.TITULAR,
            estado=estado.consentimiento.value,
            version=estado.version_consentimiento,
            version_requerida=estado.requeridas.titular,
            categoria_del_acto=estado.categoria_edad_consentimiento,
            categoria_actual=perfil.categoria_de_edad,
        )
    ]
    if estado.es_menor:
        dimensiones.append(
            DimensionDecidible(
                alcance=Alcance.ASENTIMIENTO,
                estado=estado.asentimiento.value,
                version=estado.version_asentimiento,
                version_requerida=estado.requeridas.asentimiento,
            )
        )
    return tuple(dimensiones)

def acciones_de_decision(estado: EstadoVigente) -> AccionesDeDecision:
    return acciones_disponibles(dimensiones_decidibles(estado))

def version_como_json(version) -> dict:
    return {
        "codigo": version.codigo,
        "alcance": version.alcance.value,
        "finalidades": sorted(f.value for f in version.finalidades),
        "huella_contenido": version.huella_contenido,
        "vigente_desde": version.vigente_desde.isoformat(),
        "vigente_hasta": version.vigente_hasta.isoformat() if version.vigente_hasta else None,
        "documento_disponible": True,
    }

def estado_como_json(estado: EstadoVigente, acceso: AccesoCalculado) -> dict:
    perfil = estado.perfil
    return {
        "acceso": acceso.value,
        "tutoria_academica_sin_investigacion": (
            permite_tutoria_academica(estado)
        ),
        "perfil": {
            "completo": estado.perfil_completo,
            "pendientes": list(perfil.campos_pendientes) if perfil else ["edad", "facultad", "programa", "semestre", "clase"],
            "edad": perfil.edad if perfil else None,
            "facultad": perfil.facultad if perfil else "",
            "programa": perfil.programa if perfil else "",
            "semestre": perfil.semestre if perfil else None,
            "clase_vinculada": perfil.clase_vinculada if perfil else False,
        },
        "consentimiento": {
            "estado": estado.consentimiento.value,
            "version": estado.version_consentimiento,
            "al_dia": estado.consentimiento_al_dia,
        },
        "asentimiento": {
            "estado": estado.asentimiento.value,
            "version": estado.version_asentimiento,
            "al_dia": estado.asentimiento_al_dia,
        },
        "representante": {
            "estado": estado.representante.value,
            "motivo": estado.motivo_representante or None,
            "limite": (
                estado.limite_representante.isoformat()
                if estado.limite_representante
                else None
            ),
        },
        "versiones_requeridas": {
            "titular": estado.requeridas.titular,
            "asentimiento": estado.requeridas.asentimiento,
            "representante": estado.requeridas.representante,
        },

        "decision": _decision_como_json(acciones_de_decision(estado)),
    }

def _decision_como_json(acciones: AccionesDeDecision) -> dict:
    return {
        "requerida": acciones.requerida,
        "puede_aceptar": acciones.puede_aceptar,
        "puede_rechazar": acciones.puede_rechazar,
    }

def responder_con_estado(repos: Repositorios, sujeto: str, extra: dict) -> JSONResponse:
    estado, acceso, fallo = leer_estado(repos, sujeto)
    if fallo is not None:
        return fallo
    return JSONResponse({**estado_como_json(estado, acceso), **extra})
