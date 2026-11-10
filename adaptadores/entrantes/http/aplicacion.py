from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from adaptadores.entrantes.http.composicion import componer
from adaptadores.entrantes.http.docentes import RegistroDeDocentes
from adaptadores.entrantes.http.instrumentacion import Instrumentador
from adaptadores.entrantes.http.limitador import LimitadorDePeticiones
from adaptadores.entrantes.http.rutas import (
    analitica_institucional as rutas_analitica_institucional,
)
from adaptadores.entrantes.http.rutas import (
    clases as rutas_clases,
)
from adaptadores.entrantes.http.rutas import (
    conceptos as rutas_conceptos,
)
from adaptadores.entrantes.http.rutas import (
    configuracion_sondeos as rutas_configuracion_sondeos,
)
from adaptadores.entrantes.http.rutas import (
    consentimiento as rutas_consentimiento,
)
from adaptadores.entrantes.http.rutas import (
    consumo_ia as rutas_consumo_ia,
)
from adaptadores.entrantes.http.rutas import (
    conversaciones_investigacion as rutas_conversaciones_investigacion,
)
from adaptadores.entrantes.http.rutas import (
    correos as rutas_correos,
)
from adaptadores.entrantes.http.rutas import (
    datos_personales as rutas_datos_personales,
)
from adaptadores.entrantes.http.rutas import (
    evidencias as rutas_evidencias,
)
from adaptadores.entrantes.http.rutas import (
    fuentes as rutas_fuentes,
)
from adaptadores.entrantes.http.rutas import (
    gobierno as rutas_gobierno,
)
from adaptadores.entrantes.http.rutas import (
    graficadora as rutas_graficadora,
)
from adaptadores.entrantes.http.rutas import (
    historial as rutas_historial,
)
from adaptadores.entrantes.http.rutas import (
    informes as rutas_informes,
)
from adaptadores.entrantes.http.rutas import (
    kpi as rutas_kpi,
)
from adaptadores.entrantes.http.rutas import (
    panel_docente as rutas_panel_docente,
)
from adaptadores.entrantes.http.rutas import (
    preferencias_interfaz as rutas_preferencias_interfaz,
)
from adaptadores.entrantes.http.rutas import (
    preferencias_notificacion as rutas_preferencias_notificacion,
)
from adaptadores.entrantes.http.rutas import (
    puerta_de_supresion as rutas_puerta,
)
from adaptadores.entrantes.http.rutas import recursos as rutas_recursos
from adaptadores.entrantes.http.rutas import (
    relectura_conductual as rutas_relectura_conductual,
)
from adaptadores.entrantes.http.rutas import (
    reportes as rutas_reportes,
)
from adaptadores.entrantes.http.rutas import (
    rol_docente as rutas_rol_docente,
)
from adaptadores.entrantes.http.rutas import (
    salud as rutas_salud,
)
from adaptadores.entrantes.http.rutas import (
    sesion as rutas_sesion,
)
from adaptadores.entrantes.http.rutas import (
    supervision as rutas_supervision,
)
from adaptadores.entrantes.http.rutas import (
    telemetria as rutas_telemetria,
)
from adaptadores.entrantes.http.rutas import (
    turno as rutas_turno,
)
from adaptadores.entrantes.http.sesiones import Sesiones
from adaptadores.entrantes.http.turno import AdaptadorTurno, ContenidoDelCurso
from adaptadores.salientes.almacenamiento.fotos_perfil import AlmacenFotosPerfil
from adaptadores.salientes.biblioteca import CatalogoDeFuentes
from adaptadores.salientes.conceptos import BancoDeConceptos
from adaptadores.salientes.notificacion.canal import componer_canal
from adaptadores.salientes.registro.clases_memoria import Clases
from adaptadores.salientes.registro.cola_revision_memoria import ColaDeRevision
from adaptadores.salientes.registro.consentimiento_degradado import (
    AdaptadorConsentimientoDegradado,
)
from adaptadores.salientes.registro.conversaciones_investigacion import (
    ConversacionesInvestigacionPostgres,
)
from adaptadores.salientes.registro.recursos_db import RecursosPostgres
from dominio.puertos.almacen import DatoNoAdmitido

if TYPE_CHECKING:
    from dominio.puertos.analitica_docente import PuertoAnaliticaDocente
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.consentimiento import PuertoConsentimiento
    from dominio.puertos.supervision import PuertoColaDeRevision

def _clases_almacen(faltantes: list[str]) -> PuertoClases:
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: las clases y la matrícula "
            "(DD-12) viven en memoria del proceso y un reinicio las pierde"
        )
        return Clases()
    try:
        from adaptadores.salientes.registro.clases_db import (
            AdaptadorClasesPostgres,
        )

        return AdaptadorClasesPostgres(cadena)
    except Exception as exc:
        faltantes.append(
            f"no se pudo construir el almacén de clases (DD-12) contra Postgres: {exc}"
        )
        return Clases()

def _analitica_docente(faltantes: list[str]) -> PuertoAnaliticaDocente:
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.analitica_docente_degradada import (
            AnaliticaDocenteNoConfigurada,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: la analítica docente no puede calcularse"
        )
        return AnaliticaDocenteNoConfigurada()
    from adaptadores.salientes.registro.analitica_docente_db import (
        AdaptadorAnaliticaDocentePostgres,
    )

    return AdaptadorAnaliticaDocentePostgres(cadena)

def _calculo_kpi(faltantes: list[str]):
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.kpi_degradado import (
            CalculoKPINoConfigurado,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: el catálogo KPI v1.1 no se puede calcular"
        )
        return CalculoKPINoConfigurado()
    from adaptadores.salientes.registro.kpi_db import (
        AdaptadorKPIPostgres,
    )

    return AdaptadorKPIPostgres(cadena)

def _auditor_informes():
    from adaptadores.salientes.registro.informes_db import (
        AuditorDeInformesPostgres,
    )

    return AuditorDeInformesPostgres(os.environ.get("AGENTE_BD", ""))

def _consumo_ia(faltantes: list[str]):
    from adaptadores.salientes.registro.consumo_ia_db import (
        AdaptadorConsumoIAPostgres,
    )

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: el consumo y costo institucional de IA "
            "no se registra ni se puede consultar"
        )
    return AdaptadorConsumoIAPostgres(cadena)

def _reportes(faltantes: list[str]):
    from adaptadores.salientes.registro.reportes_db import (
        AdaptadorReportesPostgres,
    )

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append("AGENTE_BD no está en el entorno: los reportes no se pueden guardar")
    return AdaptadorReportesPostgres(cadena)

def _preferencias_notificacion(faltantes: list[str]):
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.preferencias_notificacion_degradadas import (
            PreferenciasDeNotificacionNoConfiguradas,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: las preferencias de correo no se "
            "pueden consultar y todos los avisos opcionales quedan desactivados"
        )
        return PreferenciasDeNotificacionNoConfiguradas()
    from adaptadores.salientes.registro.preferencias_notificacion_db import (
        AdaptadorPreferenciasDeNotificacionPostgres,
    )

    return AdaptadorPreferenciasDeNotificacionPostgres(cadena)

def _preferencias_interfaz():
    from adaptadores.salientes.registro.preferencias_interfaz_db import (
        PreferenciasInterfazPostgres,
    )

    return PreferenciasInterfazPostgres(os.environ.get("AGENTE_BD", ""))

def _telemetria(faltantes: list[str]):
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.telemetria_degradada import (
            TelemetriaNoConfigurada,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: la telemetría de la Fase 8 no se registra"
        )
        return TelemetriaNoConfigurada()
    from adaptadores.salientes.registro.telemetria_db import (
        AdaptadorTelemetriaPostgres,
    )

    return AdaptadorTelemetriaPostgres(cadena)

def _version_del_corpus():
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        return None
    from adaptadores.salientes.corpus.version import (
        VersionDelCorpusPostgres,
    )

    return VersionDelCorpusPostgres(cadena)

def _cola_revision(faltantes: list[str]) -> PuertoColaDeRevision:
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: la cola de revisión docente "
            "(RU-12) vive en memoria del proceso y un reinicio la pierde"
        )
        return ColaDeRevision()
    try:
        from adaptadores.salientes.registro.cola_revision_db import (
            AdaptadorColaDeRevisionPostgres,
        )

        return AdaptadorColaDeRevisionPostgres(cadena)
    except Exception as exc:
        faltantes.append(f"no se pudo construir la cola de revisión (RU-12) contra Postgres: {exc}")
        return ColaDeRevision()

def _registro_docentes(faltantes: list[str]) -> RegistroDeDocentes:
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: la cola de solicitudes de rol "
            "docente (D-16 C) vive en memoria del proceso y un reinicio la "
            "pierde. La lista manual (DOCENTES_AUTORIZADOS) no depende de esto: "
            "se lee del entorno y, si no está, queda vacía."
        )
        return RegistroDeDocentes()
    try:
        from adaptadores.salientes.registro.solicitudes_docente_db import (
            AdaptadorSolicitudesDocentesPostgres,
        )

        return RegistroDeDocentes(
            adaptador_solicitudes=AdaptadorSolicitudesDocentesPostgres(cadena)
        )
    except Exception as exc:
        faltantes.append(
            f"no se pudo construir el adaptador de solicitudes docentes (D-16 C) contra Postgres: {exc}"
        )
        return RegistroDeDocentes()

def _consentimiento_almacen() -> PuertoConsentimiento:
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        return AdaptadorConsentimientoDegradado()
    from adaptadores.salientes.registro.consentimiento_db import (
        AdaptadorConsentimientoPostgres,
    )

    return AdaptadorConsentimientoPostgres(cadena)

def _identidades(faltantes: list[str]):
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: la identidad de EQ-020 no se puede "
            "persistir y POST /api/sesion/google responde mantenimiento"
        )
        return None
    try:
        from adaptadores.salientes.registro.identidad_db import (
            AdaptadorIdentidadPostgres,
        )

        return AdaptadorIdentidadPostgres(cadena)
    except Exception as exc:
        faltantes.append(f"no se pudo construir el registro de identidad (EQ-020): {exc}")
        return None

def _repositorios_de_consentimiento(
    identidades, faltantes: list[str], notificacion, almacenamiento
):

    from adaptadores.entrantes.http.rutas import consentimiento as rutas_c

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena or identidades is None:

        return None
    try:
        from adaptadores.salientes.registro.consentimiento_versionado_db import (
            AdaptadorEventosDeConsentimientoPostgres,
            AdaptadorVersionesDeConsentimientoPostgres,
        )
        from adaptadores.salientes.registro.decision_conjunta_db import (
            AdaptadorDecisionConjuntaPostgres,
        )
        from adaptadores.salientes.registro.estado_vigente_db import (
            AdaptadorEstadoVigentePostgres,
        )
        from adaptadores.salientes.registro.menores_db import (
            AdaptadorAsentimientoPostgres,
            AdaptadorEvidenciaDelRepresentantePostgres,
        )

        return rutas_c.Repositorios(
            identidades=identidades,
            versiones=(_versiones := AdaptadorVersionesDeConsentimientoPostgres(cadena)),

            instantaneas=_versiones,
            eventos=AdaptadorEventosDeConsentimientoPostgres(cadena),
            asentimientos=AdaptadorAsentimientoPostgres(cadena),
            evidencias=AdaptadorEvidenciaDelRepresentantePostgres(cadena),
            estado_vigente=AdaptadorEstadoVigentePostgres(cadena),
            almacenamiento=almacenamiento,

            decision_conjunta=AdaptadorDecisionConjuntaPostgres(cadena),

            notificacion=notificacion,
        )
    except Exception as exc:
        faltantes.append(f"no se pudo construir la frontera de consentimiento (EQ-021): {exc}")
        return None

def _almacenamiento_privado(faltantes: list[str]):
    from adaptadores.salientes.almacenamiento.no_configurado import (
        AlmacenamientoNoConfiguradoAdaptador,
    )
    from adaptadores.salientes.almacenamiento.sistema_de_archivos import (
        ConfiguracionInvalida,
        desde_entorno,
    )

    try:
        custodia = desde_entorno()
    except ConfiguracionInvalida as exc:
        faltantes.append(
            "el almacenamiento privado de la autorización del representante (EQ-021) "
            f"está declarado y no se puede usar: {exc}"
        )
        return AlmacenamientoNoConfiguradoAdaptador()
    if custodia is not None:
        return custodia

    faltantes.append(
        "el almacenamiento privado de la autorización del representante (EQ-021) no "
        "está configurado: falta declarar la ruta del volumen privado en el entorno"
    )
    return AlmacenamientoNoConfiguradoAdaptador()

def _consentimiento_sin_base(notificacion, almacenamiento):
    from adaptadores.entrantes.http.rutas import consentimiento as rutas_c
    from adaptadores.salientes.registro.consentimiento_versionado_db import (
        AdaptadorEventosDeConsentimientoPostgres,
        AdaptadorVersionesDeConsentimientoPostgres,
    )
    from adaptadores.salientes.registro.decision_conjunta_degradada import (
        AdaptadorDecisionConjuntaDegradado,
    )
    from adaptadores.salientes.registro.estado_vigente_db import (
        AdaptadorEstadoVigentePostgres,
    )
    from adaptadores.salientes.registro.identidad_db import (
        AdaptadorIdentidadPostgres,
    )
    from adaptadores.salientes.registro.menores_db import (
        AdaptadorAsentimientoPostgres,
        AdaptadorEvidenciaDelRepresentantePostgres,
    )

    return rutas_c.Repositorios(
        identidades=AdaptadorIdentidadPostgres(""),
        versiones=AdaptadorVersionesDeConsentimientoPostgres(""),
        eventos=AdaptadorEventosDeConsentimientoPostgres(""),
        asentimientos=AdaptadorAsentimientoPostgres(""),
        evidencias=AdaptadorEvidenciaDelRepresentantePostgres(""),
        estado_vigente=AdaptadorEstadoVigentePostgres(""),
        almacenamiento=almacenamiento,
        decision_conjunta=AdaptadorDecisionConjuntaDegradado(),
        notificacion=notificacion,
    )

def _repositorios_de_gobierno(faltantes: list[str], notificacion, identidades=None):
    from adaptadores.entrantes.http.rutas import gobierno as rutas_g

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        return None
    try:
        from adaptadores.entrantes.http.investigadores import (
            propietarios_configurados,
        )
        from adaptadores.salientes.registro.gobierno_db import (
            AdaptadorAuditoriaPostgres,
            AdaptadorPropuestasPostgres,
            AdaptadorRetencionPostgres,
            AdaptadorSolicitudesDeSupresionPostgres,
        )
        from adaptadores.salientes.registro.inventario_db import (
            AdaptadorInventarioPostgres,
        )
        from adaptadores.salientes.registro.invitaciones_db import (
            AdaptadorInvitacionesPostgres,
        )
        from adaptadores.salientes.registro.roles_db import (
            AdaptadorRolesPostgres,
        )
        return rutas_g.RepositoriosDeGobierno(
            supresiones=AdaptadorSolicitudesDeSupresionPostgres(cadena),
            retencion=AdaptadorRetencionPostgres(cadena),
            auditoria=AdaptadorAuditoriaPostgres(cadena),
            inventario=AdaptadorInventarioPostgres(cadena),
            roles=AdaptadorRolesPostgres(cadena),
            notificacion=notificacion,

            propuestas=AdaptadorPropuestasPostgres(cadena),
            identidades=identidades,
            invitaciones=AdaptadorInvitacionesPostgres(
                cadena, propietarios_configurados()
            ),
        )
    except Exception as exc:
        faltantes.append(f"no se pudo construir el gobierno de datos (EQ-022): {exc}")
        return None

def _gobierno_sin_base(notificacion):
    from adaptadores.entrantes.http.rutas import gobierno as rutas_g
    from adaptadores.salientes.registro.gobierno_db import (
        AdaptadorAuditoriaPostgres,
        AdaptadorPropuestasPostgres,
        AdaptadorRetencionPostgres,
        AdaptadorSolicitudesDeSupresionPostgres,
    )
    from adaptadores.salientes.registro.inventario_db import (
        AdaptadorInventarioPostgres,
    )
    from adaptadores.salientes.registro.invitaciones_db import (
        AdaptadorInvitacionesPostgres,
    )
    from adaptadores.salientes.registro.roles_db import (
        AdaptadorRolesPostgres,
    )

    return rutas_g.RepositoriosDeGobierno(
        supresiones=AdaptadorSolicitudesDeSupresionPostgres(""),
        retencion=AdaptadorRetencionPostgres(""),
        auditoria=AdaptadorAuditoriaPostgres(""),
        inventario=AdaptadorInventarioPostgres(""),
        roles=AdaptadorRolesPostgres(""),
        notificacion=notificacion,
        propuestas=AdaptadorPropuestasPostgres(""),
        invitaciones=AdaptadorInvitacionesPostgres(""),
    )

def _monitor_de_disponibilidad(canal, faltantes: list[str]):
    from adaptadores.salientes.disponibilidad.postgres import (
        MonitorDeDisponibilidad,
        sondear_postgres,
    )

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: la vigilancia de disponibilidad de "
            "EQ-024 no se inicia y nadie avisará si la base deja de responder"
        )
        return None
    return MonitorDeDisponibilidad(
        sondear=lambda: sondear_postgres(cadena),
        notificar=canal.puerto,
        destino=canal.destino_operativo,
    )

def _trabajos_relectura():
    from adaptadores.salientes.registro.trabajos_relectura import (
        TrabajosRelecturaPostgres,
    )

    return TrabajosRelecturaPostgres(os.environ.get("AGENTE_BD", ""))

def crear_aplicacion() -> FastAPI:
    faltantes_almacenes: list[str] = []

    canal = componer_canal()
    faltantes_almacenes.extend(canal.faltantes())
    monitor = _monitor_de_disponibilidad(canal, faltantes_almacenes)

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):
        from adaptadores.salientes.disponibilidad.postgres import (
            vigilancia,
        )

        async with vigilancia(monitor):
            yield

    app = FastAPI(
        title="Agente de cálculo diferencial",
        docs_url=None,
        redoc_url=None,
        lifespan=ciclo_de_vida,
    )

    composicion = componer()

    adaptador_perfil = composicion.adaptador_perfil

    contenido = Path(__file__).resolve().parents[3] / "contenido"
    banco = BancoDeConceptos(contenido / "conceptos")

    catalogo_de_fuentes = CatalogoDeFuentes.desde_directorio(contenido / "corpus")
    faltantes_almacenes.extend(
        f"biblioteca de fuentes: {f}" for f in catalogo_de_fuentes.informe.fallos
    )

    adaptador = AdaptadorTurno(
        composicion.orquestador,
        contexto_reforzado=composicion.contexto_reforzado,
        continuidad=composicion.continuidad,
        adaptador_perfil=adaptador_perfil,

        plantillas=composicion.plantillas,

        contenido=ContenidoDelCurso(banco=banco, catalogo=catalogo_de_fuentes),
    )

    sesiones = Sesiones()

    limitador = LimitadorDePeticiones()

    clases_almacen = _clases_almacen(faltantes_almacenes)
    analitica_docente = _analitica_docente(faltantes_almacenes)

    telemetria = _telemetria(faltantes_almacenes)
    instrumentador = Instrumentador(telemetria, _version_del_corpus())
    calculo_kpi = _calculo_kpi(faltantes_almacenes)
    auditor_informes = _auditor_informes()
    consumo_ia = _consumo_ia(faltantes_almacenes)
    reportes = _reportes(faltantes_almacenes)
    preferencias_notificacion = _preferencias_notificacion(faltantes_almacenes)
    cola = _cola_revision(faltantes_almacenes)
    registro_docentes = _registro_docentes(faltantes_almacenes)

    consentimiento_almacen = _consentimiento_almacen()

    identidades = _identidades(faltantes_almacenes)

    almacenamiento_privado = _almacenamiento_privado(faltantes_almacenes)

    fotos_perfil = AlmacenFotosPerfil.desde_entorno()
    if not fotos_perfil.configurado:
        faltantes_almacenes.append("FOTOS_PERFIL_RUTA no apunta a una custodia privada escribible")

    consentimiento_b2 = _repositorios_de_consentimiento(
        identidades, faltantes_almacenes, canal.puerto, almacenamiento_privado
    )

    repos_b2 = consentimiento_b2 or _consentimiento_sin_base(canal.puerto, almacenamiento_privado)

    repos_gobierno = _repositorios_de_gobierno(
        faltantes_almacenes, canal.puerto, identidades
    ) or _gobierno_sin_base(canal.puerto)

    puerta_supresion = rutas_puerta.PuertaDeSupresion(repos_b2.estado_vigente)
    recursos_almacen = RecursosPostgres(os.environ.get('AGENTE_BD', ''))

    for router in (
        rutas_recursos.crear_router(
            sesiones, recursos_almacen,
            puerta_supresion, repos_b2.estado_vigente,
        ),
        rutas_salud.crear_router(
            composicion,
            faltantes_almacenes,
            canal=canal,
            monitor=monitor,

            almacenamiento=almacenamiento_privado,
            versiones=consentimiento_b2.versiones if consentimiento_b2 else None,
        ),
        rutas_sesion.crear_router(
            sesiones,
            registro_docentes,
            consentimiento_almacen,
            identidades,

            roles=repos_gobierno.roles,
            fotos=fotos_perfil,
            invitaciones=repos_gobierno.invitaciones,
        ),
        rutas_turno.crear_router(
            rutas_turno.DependenciasDelTurno(
                sesiones=sesiones,
                adaptador=adaptador,
                limitador=limitador,
                clases_almacen=clases_almacen,
                cola=cola,
                adaptador_historial=composicion.adaptador_historial,

                estado_vigente=(consentimiento_b2.estado_vigente if consentimiento_b2 else None),
                instrumentador=instrumentador,
            )
        ),

        rutas_supervision.crear_router(
            sesiones, cola, puerta_supresion, clases_almacen, instrumentador
        ),
        rutas_clases.crear_router(
            sesiones, clases_almacen, puerta_supresion, fotos_perfil, canal.puerto,
            preferencias_notificacion,
            correo_investigacion=canal.destino_investigacion,
        ),
        rutas_rol_docente.crear_router(sesiones, registro_docentes, puerta_supresion),

        rutas_datos_personales.crear_router(sesiones, identidades, fotos_perfil, puerta_supresion, _preferencias_interfaz(), recursos_almacen),
        rutas_preferencias_notificacion.crear_router(
            sesiones, preferencias_notificacion, puerta_supresion
        ),
        rutas_preferencias_interfaz.crear_router(sesiones, _preferencias_interfaz(), puerta_supresion),
        rutas_configuracion_sondeos.crear_router(
            sesiones, composicion.configuracion_sondeos, puerta_supresion
        ),
        rutas_conceptos.crear_router(banco),
        rutas_graficadora.crear_router(sesiones),

        rutas_fuentes.crear_router(catalogo_de_fuentes, sesiones),

        rutas_consentimiento.crear_router(sesiones, repos_b2),

        rutas_evidencias.crear_router(
            sesiones,
            rutas_evidencias.DependenciasDeEvidencias(
                evidencias=repos_b2.evidencias,
                almacenamiento=repos_b2.almacenamiento,
            ),

            puerta_supresion,
        ),

        rutas_gobierno.crear_router(sesiones, repos_gobierno, puerta_supresion),

        rutas_correos.crear_router(
            sesiones,
            canal.puerto,
            repos_gobierno.auditoria,
            puerta_supresion,
            canal_configurado=canal.envia,
        ),
        rutas_reportes.crear_router(sesiones, reportes, puerta_supresion),

        rutas_conversaciones_investigacion.crear_router(
            sesiones,
            ConversacionesInvestigacionPostgres(os.environ.get('AGENTE_BD', '')),
            puerta_supresion, catalogo_de_fuentes,
        ),
        rutas_historial.crear_router(
            sesiones, composicion.adaptador_historial, catalogo_de_fuentes
        ),
        rutas_panel_docente.crear_router(
            sesiones, analitica_docente, puerta_supresion, clases_almacen, instrumentador,
            calculo_kpi,
        ),

        rutas_telemetria.crear_router(sesiones, telemetria, puerta_supresion),

        rutas_kpi.crear_router(sesiones, calculo_kpi, puerta_supresion),
        rutas_relectura_conductual.crear_router(
            sesiones, _trabajos_relectura(), puerta_supresion
        ),
        rutas_informes.crear_router(
            sesiones, calculo_kpi, auditor_informes, puerta_supresion
        ),
        rutas_consumo_ia.crear_router(sesiones, consumo_ia, puerta_supresion),
        rutas_analitica_institucional.crear_router(
            sesiones,
            analitica_docente,
            puerta_supresion,
            repos_gobierno.roles,
            identidades,
            fotos_perfil,
            calculo_kpi,
            consumo_ia,
        ),
    ):
        app.include_router(router)

    @app.exception_handler(DatoNoAdmitido)
    async def _dato_no_admitido(_peticion: Request, _error: DatoNoAdmitido) -> JSONResponse:
        return JSONResponse(
            {"detalle": "la petición contiene un valor que no se puede procesar"},
            status_code=400,
        )

    return app

app = crear_aplicacion()
