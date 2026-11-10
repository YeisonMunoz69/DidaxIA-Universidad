"""
aplicacion.py — La aplicación HTTP · `ADR-009`
================================================

Lo que faltaba para que el frontend tuviera con quién hablar. Hasta el
2026-08-10 `adaptadores/entrantes/http/` tenía `AdaptadorTurno` —una clase con
un método `manejar()`— y **ninguna ruta**: `PM-F02` lo descubrió al intentar
comprobar la conversación de punta a punta.

Este archivo hace DOS cosas, y desde `PM-B27` solo dos
--------------------------------------------------------------
1. **Construir el estado compartido**: la composición del dominio y los cuatro
   almacenes en memoria del proceso.
2. **Registrar los routers** de `rutas/`, uno por familia.

Las rutas ya no viven aquí. Llegó a tener las 33 en un solo
`crear_aplicacion()` de 823 líneas, y creció así porque partirlo «no era el
encargo» de ninguna de las sesiones que le fueron añadiendo rutas encima
—`PM-B14`, `PM-B19`, `PM-B21`, `PM-B15`, `DD-26`—. `PM-B27` lo repartió: ver
`rutas/__init__.py` para la convención y por qué las dependencias entran por
parámetro y no por `Depends`.

`08-Contrato-del-Turno.md` §12 deja fuera del contrato «las rutas HTTP, los
verbos y los códigos de estado» porque son del adaptador. El cliente las
propuso en `frontend/src/nucleo/api/cliente.js`; aquí se aceptan tal cual, de
modo que las dos orillas coinciden y el ajuste, si algún día lo hay, es un
archivo a cada lado.

Lo que este módulo NO hace, y se declara en vez de simularse
-------------------------------------------------------------
**`Sesiones` no persiste, y es correcto por diseño.** `RP-02` pide conservar
el identificador durante la sesión, no entre despliegues — ver el docstring
de `sesiones.py`. Con `AGENTE_BD` puesta, `Clases`, la cola de revisión
(`RU-12`) y las solicitudes de rol docente (`D-16` C) sí persisten desde el
2026-08-22 —`_clases_almacen()` y compañía, más abajo—; sin ella, caen al
mismo respaldo en memoria de siempre y `GET /api/salud` lo declara. Lo que
siempre sobrevivió son el perfil versionado (`PM-B11`) y el registro del
turno (`PM-B20`), que tienen su propio adaptador contra la base.

**El consentimiento también entra por la composición desde la Fase 2 ·
sesión 3.** `rutas/sesion.py` llamaba a dos funciones de módulo que resolvían
la base contra una `AGENTE_BD` capturada al importar `consentimiento_db.py`.
Ahora `_consentimiento_almacen()` decide —PostgreSQL o el degradado, que no
guarda— y la ruta recibe la dependencia. La política de consentimiento no
cambió: sin base sigue sin persistirse nada, igual que antes.

**El árbol del docente ya tiene almacén, y sigue sin persistir.**
`/api/contexto-curricular` y `/api/grupo` siguen declarados sin alimentar —
ver `rutas/panel_docente.py`, que es donde se explica por qué siguen vacías.

**La cola de supervisión solo recibe la excepción, no el muestreo.** Ver el
docstring de `supervision.py` sobre por qué el muestreo aleatorio no está
implementado.
"""

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

if TYPE_CHECKING:  # pragma: no cover
    from dominio.puertos.analitica_docente import PuertoAnaliticaDocente
    from dominio.puertos.clases import PuertoClases
    from dominio.puertos.consentimiento import PuertoConsentimiento
    from dominio.puertos.supervision import PuertoColaDeRevision


def _clases_almacen(faltantes: list[str]) -> PuertoClases:
    """`Clases` en Postgres (`08-clases.sql`) cuando `AGENTE_BD` está, o el
    respaldo en memoria de siempre — mismo criterio que
    `composicion.py::_perfil()`. Los dos satisfacen `PuertoClases`
    (`dominio/puertos/clases.py`): ninguna ruta necesita saber cuál recibió.

    ✅ **2026-08-22.** Hasta hoy no había otra opción que memoria, y el
    docstring de `Clases` ya lo declaraba. Ahora la ausencia de `AGENTE_BD`
    es una degradación explícita, la misma disciplina que el resto de piezas
    que dependen de la base — no un límite fijo del sistema.
    """
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: las clases y la matrícula "
            "(DD-12) viven en memoria del proceso y un reinicio las pierde"
        )
        return Clases()
    try:
        from adaptadores.salientes.registro.clases_db import (  # noqa: PLC0415
            AdaptadorClasesPostgres,
        )

        return AdaptadorClasesPostgres(cadena)
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(
            f"no se pudo construir el almacén de clases (DD-12) contra Postgres: {exc}"
        )
        return Clases()


def _analitica_docente(faltantes: list[str]) -> PuertoAnaliticaDocente:
    """El agregado docente es una lectura PostgreSQL; sin base falla cerrado."""
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.analitica_docente_degradada import (  # noqa: PLC0415
            AnaliticaDocenteNoConfigurada,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: la analítica docente no puede calcularse"
        )
        return AnaliticaDocenteNoConfigurada()
    from adaptadores.salientes.registro.analitica_docente_db import (  # noqa: PLC0415
        AdaptadorAnaliticaDocentePostgres,
    )

    return AdaptadorAnaliticaDocentePostgres(cadena)


def _calculo_kpi(faltantes: list[str]):
    """El catálogo KPI v1.1 calculado contra PostgreSQL, o cerrado.

    Sin base no se degrada a un catálogo con ceros: un tablero lleno de ceros
    por falta de base es el silencio que el encargo prohíbe. La ruta traduce el
    cierre a mantenimiento, que sí dice lo que ocurre.
    """
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.kpi_degradado import (  # noqa: PLC0415
            CalculoKPINoConfigurado,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: el catálogo KPI v1.1 no se puede calcular"
        )
        return CalculoKPINoConfigurado()
    from adaptadores.salientes.registro.kpi_db import (  # noqa: PLC0415
        AdaptadorKPIPostgres,
    )

    return AdaptadorKPIPostgres(cadena)


def _auditor_informes():
    from adaptadores.salientes.registro.informes_db import (  # noqa: PLC0415
        AuditorDeInformesPostgres,
    )

    return AuditorDeInformesPostgres(os.environ.get("AGENTE_BD", ""))


def _consumo_ia(faltantes: list[str]):
    """Registro y lectura financiera; sin base existe la ruta y falla cerrada."""
    from adaptadores.salientes.registro.consumo_ia_db import (  # noqa: PLC0415
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
    """Incidencias persistentes; sin base no se ofrece un éxito en memoria."""
    from adaptadores.salientes.registro.reportes_db import (  # noqa: PLC0415
        AdaptadorReportesPostgres,
    )

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append("AGENTE_BD no está en el entorno: los reportes no se pueden guardar")
    return AdaptadorReportesPostgres(cadena)


def _preferencias_notificacion(faltantes: list[str]):
    """Preferencias persistentes; sin base todo correo opcional queda apagado."""
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.preferencias_notificacion_degradadas import (  # noqa: PLC0415
            PreferenciasDeNotificacionNoConfiguradas,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: las preferencias de correo no se "
            "pueden consultar y todos los avisos opcionales quedan desactivados"
        )
        return PreferenciasDeNotificacionNoConfiguradas()
    from adaptadores.salientes.registro.preferencias_notificacion_db import (  # noqa: PLC0415
        AdaptadorPreferenciasDeNotificacionPostgres,
    )

    return AdaptadorPreferenciasDeNotificacionPostgres(cadena)


def _preferencias_interfaz():
    from adaptadores.salientes.registro.preferencias_interfaz_db import (
        PreferenciasInterfazPostgres,  # noqa: PLC0415
    )

    return PreferenciasInterfazPostgres(os.environ.get("AGENTE_BD", ""))


def _telemetria(faltantes: list[str]):
    """El escritor de eventos de la Fase 8, o uno que falla cerrado.

    Mismo criterio que `_analitica_docente()`: sin base no se degrada a memoria.
    Una telemetría en memoria perdería los hechos al reiniciar y produciría
    series con huecos que nadie podría distinguir de una caída real de uso.
    """
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        from adaptadores.salientes.registro.telemetria_degradada import (  # noqa: PLC0415
            TelemetriaNoConfigurada,
        )

        faltantes.append(
            "AGENTE_BD no está en el entorno: la telemetría de la Fase 8 no se registra"
        )
        return TelemetriaNoConfigurada()
    from adaptadores.salientes.registro.telemetria_db import (  # noqa: PLC0415
        AdaptadorTelemetriaPostgres,
    )

    return AdaptadorTelemetriaPostgres(cadena)


def _version_del_corpus():
    """De dónde sale la huella del corpus, o `None` si no hay base.

    `None` y no un objeto degradado: el instrumentador ya trata la ausencia
    devolviendo cadena vacía, que el catálogo lee como «no consta». Un objeto
    que levantara para que otro lo capturase habría sido una vuelta de más.
    """
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        return None
    from adaptadores.salientes.corpus.version import (  # noqa: PLC0415
        VersionDelCorpusPostgres,
    )

    return VersionDelCorpusPostgres(cadena)


def _cola_revision(faltantes: list[str]) -> PuertoColaDeRevision:
    """La cola de `RU-12` en Postgres (`09-cola-revision.sql`), o memoria.
    Mismo criterio que `_clases_almacen()` — ver su docstring."""
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: la cola de revisión docente "
            "(RU-12) vive en memoria del proceso y un reinicio la pierde"
        )
        return ColaDeRevision()
    try:
        from adaptadores.salientes.registro.cola_revision_db import (  # noqa: PLC0415
            AdaptadorColaDeRevisionPostgres,
        )

        return AdaptadorColaDeRevisionPostgres(cadena)
    except Exception as exc:  # noqa: BLE001
        faltantes.append(f"no se pudo construir la cola de revisión (RU-12) contra Postgres: {exc}")
        return ColaDeRevision()


def _registro_docentes(faltantes: list[str]) -> RegistroDeDocentes:
    """`RegistroDeDocentes` con la mitad de `_solicitudes` en Postgres
    (`10-solicitud-docente.sql`) cuando `AGENTE_BD` está — la lista manual
    (`DOCENTES_AUTORIZADOS`) no depende de esto, ver el docstring de la
    clase. Sin `AGENTE_BD`, exactamente el mismo `RegistroDeDocentes()` de
    siempre.

    ⚠️ Desde el hito R7-C esa lista manual es **fail-closed**: sin
    `DOCENTES_AUTORIZADOS` no hay ninguna cuenta docente, y ya no existen
    cuentas de prueba por defecto. Un despliegue sin la variable arranca sin
    docentes por esa vía, y eso es correcto: el aviso de abajo habla sólo de la
    cola persistida, que es la mitad que sí necesita base."""
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
        from adaptadores.salientes.registro.solicitudes_docente_db import (  # noqa: PLC0415
            AdaptadorSolicitudesDocentesPostgres,
        )

        return RegistroDeDocentes(
            adaptador_solicitudes=AdaptadorSolicitudesDocentesPostgres(cadena)
        )
    except Exception as exc:  # noqa: BLE001
        faltantes.append(
            f"no se pudo construir el adaptador de solicitudes docentes (D-16 C) contra Postgres: {exc}"
        )
        return RegistroDeDocentes()


def _consentimiento_almacen() -> PuertoConsentimiento:
    """El almacén de consentimiento: PostgreSQL (`07-consentimiento-usuario.sql`) si
    `AGENTE_BD` está, y el degradado —que no guarda nada— si no.

    ⚠️ **No añade nada a `faltantes`, y es a propósito.** `GET /api/salud`
    publica una lista de mensajes que el frontend muestra; añadir una línea
    nueva cambiaría esa respuesta, y esta sesión (Fase 2 · 3) tiene prohibido
    cambiar la API. Que el consentimiento no persista sin base es exactamente
    lo que ya pasaba antes de inyectar la dependencia.

    Sí es una brecha real, y está anotada como deuda: la Fase 3 (`EQ-016`)
    decide si el sistema puede seguir operando sin poder persistir un
    consentimiento, y ese es el momento de declararlo en la salud.

    A diferencia de los otros tres constructores, aquí no hace falta `try`:
    `AdaptadorConsentimientoPostgres.__init__` solo guarda la cadena y sus dos
    métodos ya tratan el fallo del almacén como un aviso, igual que antes.
    """
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        return AdaptadorConsentimientoDegradado()
    from adaptadores.salientes.registro.consentimiento_db import (  # noqa: PLC0415
        AdaptadorConsentimientoPostgres,
    )

    return AdaptadorConsentimientoPostgres(cadena)


def _identidades(faltantes: list[str]):
    """El registro persistente de identidad (`persona`, migración 11), o `None`.

    A diferencia de `_consentimiento_almacen()`, **esto sí declara su ausencia**
    en `faltantes`, y la diferencia es el hito B1: desde él una sesión no existe
    sin identidad persistida, así que sin este adaptador **nadie puede iniciar
    sesión**. Callarlo dejaría a quien depure un 503 sin saber si le falta
    configuración o si la base está caída, que es justo lo que `A4` cerró para
    los otros adaptadores.

    Devolver `None` en vez de un degradado es deliberado: un degradado que
    fingiera registrar la identidad produciría exactamente el éxito simulado que
    `EQ-024` prohíbe. `rutas/sesion.py` responde mantenimiento.
    """
    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: la identidad de EQ-020 no se puede "
            "persistir y POST /api/sesion/google responde mantenimiento"
        )
        return None
    try:
        from adaptadores.salientes.registro.identidad_db import (  # noqa: PLC0415
            AdaptadorIdentidadPostgres,
        )

        return AdaptadorIdentidadPostgres(cadena)
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(f"no se pudo construir el registro de identidad (EQ-020): {exc}")
        return None


def _repositorios_de_consentimiento(
    identidades, faltantes: list[str], notificacion, almacenamiento
):
    """La frontera versionada de `EQ-021` cableada, o `None` sin base.

    `None` y no un degradado, por la misma razón que `_identidades()`: un
    degradado que fingiera guardar un consentimiento produciría exactamente el
    éxito simulado que `EQ-024` prohíbe, y sobre un consentimiento eso no es un
    fallo técnico sino una autorización inventada.

    ⚠️ **`almacenamiento` llega compuesto y no se construye aquí** · `D3`. Hasta
    hoy esta función llamaba a `_almacenamiento_privado()` y
    `_consentimiento_sin_base()` construía el suyo, así que un despliegue con
    custodia configurada y sin `AGENTE_BD` acababa con el adaptador que no
    guarda nada, y `/api/salud` podía decir una cosa mientras la carga hacía
    otra. Es el mismo defecto que `D2` cerró con el canal de avisos y se cierra
    igual: una sola instancia, compuesta en `crear_aplicacion()`.
    """
    from adaptadores.entrantes.http.rutas import consentimiento as rutas_c  # noqa: PLC0415

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena or identidades is None:
        # `_identidades()` ya declaró la carencia; no se repite la línea.
        return None
    try:
        from adaptadores.salientes.registro.consentimiento_versionado_db import (  # noqa: PLC0415
            AdaptadorEventosDeConsentimientoPostgres,
            AdaptadorVersionesDeConsentimientoPostgres,
        )
        from adaptadores.salientes.registro.decision_conjunta_db import (  # noqa: PLC0415
            AdaptadorDecisionConjuntaPostgres,
        )
        from adaptadores.salientes.registro.estado_vigente_db import (  # noqa: PLC0415
            AdaptadorEstadoVigentePostgres,
        )
        from adaptadores.salientes.registro.menores_db import (  # noqa: PLC0415
            AdaptadorAsentimientoPostgres,
            AdaptadorEvidenciaDelRepresentantePostgres,
        )

        return rutas_c.Repositorios(
            identidades=identidades,
            versiones=(_versiones := AdaptadorVersionesDeConsentimientoPostgres(cadena)),
            # `§8` · el MISMO adaptador sirve los dos contratos: publicar una
            # version y leer su documento son la misma tabla y la misma
            # transaccion. Dos instancias habrian abierto dos conexiones para
            # lo mismo.
            instantaneas=_versiones,
            eventos=AdaptadorEventosDeConsentimientoPostgres(cadena),
            asentimientos=AdaptadorAsentimientoPostgres(cadena),
            evidencias=AdaptadorEvidenciaDelRepresentantePostgres(cadena),
            estado_vigente=AdaptadorEstadoVigentePostgres(cadena),
            almacenamiento=almacenamiento,
            # `D1B` · la única acción visible. Va con la MISMA cadena que los
            # demás y no con una propia: dos cadenas serían dos bases, y la
            # atomicidad que este adaptador garantiza sólo vale dentro de una.
            decision_conjunta=AdaptadorDecisionConjuntaPostgres(cadena),
            # `D2` · el mismo canal que gobierno. Ver `crear_aplicacion()`.
            notificacion=notificacion,
        )
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(f"no se pudo construir la frontera de consentimiento (EQ-021): {exc}")
        return None


def _almacenamiento_privado(faltantes: list[str]):
    """Dónde vive el PDF del representante · `EQ-021`, decidido en `D3`.

    Tres respuestas, y las tres son estados reales de un despliegue:

    1. **`ALMACENAMIENTO_PRIVADO_RUTA` ausente** → el adaptador que falla
       cerrado, y la carencia declarada. Es lo que había antes de `D3` y sigue
       siendo correcto: un despliegue sin custodia no acepta autorizaciones.
    2. **La variable declara un volumen utilizable** → el adaptador de sistema de
       archivos, y ninguna línea en `faltantes`: no falta nada.
    3. **La variable está y no sirve** —no existe, no es un directorio, no se
       puede escribir— → **también** el adaptador que falla cerrado, y una línea
       distinta. Falla cerrado a propósito: quien la escribió creía haber
       configurado la custodia, y crear la carpeta por él la habría puesto donde
       nadie respalda. Lo que no ocurre en ninguno de los tres casos es caer a
       memoria, escribir dentro del repositorio o fingir disponibilidad.

    ⚠️ **El motivo del tercer caso no lleva la ruta.** `ConfiguracionInvalida` ya
    está redactada sin ella —ver
    `adaptadores/salientes/almacenamiento/sistema_de_archivos.py`— y aquí no se
    vuelve a añadir: `faltantes` se publica entero en `GET /api/salud`, que
    contesta a cualquiera.
    """
    from adaptadores.salientes.almacenamiento.no_configurado import (  # noqa: PLC0415
        AlmacenamientoNoConfiguradoAdaptador,
    )
    from adaptadores.salientes.almacenamiento.sistema_de_archivos import (  # noqa: PLC0415
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
    """Unos `Repositorios` cuyos puertos no responden, para registrar el router.

    Las rutas existen y contestan mantenimiento en vez de 404. La diferencia
    importa para quien depura: un 404 dice «este backend no tiene esa ruta» y un
    503 dice «la tiene y no puede atenderla», que es lo cierto.

    ⚠️ **`almacenamiento` es el MISMO objeto que recibe la composición con base**
    · `D3`. Antes se construía aquí un `AlmacenamientoNoConfiguradoAdaptador()`
    propio, y eso hacía que un despliegue con volumen privado configurado y sin
    `AGENTE_BD` tuviera dos respuestas distintas a «¿hay custodia?» según por
    dónde se preguntara. Sin base sigue sin poder aceptarse una evidencia —la
    fila no entra— pero el motivo que se publica es el verdadero.
    """
    from adaptadores.entrantes.http.rutas import consentimiento as rutas_c  # noqa: PLC0415
    from adaptadores.salientes.registro.consentimiento_versionado_db import (  # noqa: PLC0415
        AdaptadorEventosDeConsentimientoPostgres,
        AdaptadorVersionesDeConsentimientoPostgres,
    )
    from adaptadores.salientes.registro.decision_conjunta_degradada import (  # noqa: PLC0415
        AdaptadorDecisionConjuntaDegradado,
    )
    from adaptadores.salientes.registro.estado_vigente_db import (  # noqa: PLC0415
        AdaptadorEstadoVigentePostgres,
    )
    from adaptadores.salientes.registro.identidad_db import (  # noqa: PLC0415
        AdaptadorIdentidadPostgres,
    )
    from adaptadores.salientes.registro.menores_db import (  # noqa: PLC0415
        AdaptadorAsentimientoPostgres,
        AdaptadorEvidenciaDelRepresentantePostgres,
    )

    # Cadena vacía: cada repositorio levanta `AlmacenNoConfigurado` en su primera
    # operación, que es exactamente lo que las rutas traducen a mantenimiento.
    #
    # La decisión conjunta usa el adaptador **degradado** y no uno de PostgreSQL
    # con cadena vacía: los dos se niegan, pero aquél no tiene ninguna cadena que
    # nadie pueda rellenar después, y la única acción visible del recorrido es el
    # peor sitio donde admitir una aceptación aparente.
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
    """La frontera de `EQ-022`/`EQ-023` cableada, o `None` sin base.

    Mismo criterio que `_identidades()` y `_repositorios_de_consentimiento()`:
    `None` y no un degradado. Un trámite de supresión que se «registrara» en
    memoria y se perdiera en el reinicio sería el peor éxito simulado del
    sistema — la persona creería haber ejercido un derecho.

    ⚠️ **`notificacion` llega compuesta y no se construye aquí** (`D2`). Hasta
    hoy esta función creaba su propio `NotificacionRegistrada()` y declaraba a
    pelo que el canal no existía. Con Resend detrás del puerto eso habría dado
    dos instancias —una aquí, otra en el recorrido del consentimiento— y, el día
    que una se configurara y la otra no, dos respuestas distintas a «¿salió el
    aviso?» dentro del mismo despliegue. Ver `crear_aplicacion()`.
    """
    from adaptadores.entrantes.http.rutas import gobierno as rutas_g  # noqa: PLC0415

    cadena = os.environ.get("AGENTE_BD", "")
    if not cadena:
        return None
    try:
        from adaptadores.entrantes.http.investigadores import (  # noqa: PLC0415
            propietarios_configurados,
        )
        from adaptadores.salientes.registro.gobierno_db import (  # noqa: PLC0415
            AdaptadorAuditoriaPostgres,
            AdaptadorPropuestasPostgres,
            AdaptadorRetencionPostgres,
            AdaptadorSolicitudesDeSupresionPostgres,
        )
        from adaptadores.salientes.registro.inventario_db import (  # noqa: PLC0415
            AdaptadorInventarioPostgres,
        )
        from adaptadores.salientes.registro.invitaciones_db import (  # noqa: PLC0415
            AdaptadorInvitacionesPostgres,
        )
        from adaptadores.salientes.registro.roles_db import (  # noqa: PLC0415
            AdaptadorRolesPostgres,
        )
        return rutas_g.RepositoriosDeGobierno(
            supresiones=AdaptadorSolicitudesDeSupresionPostgres(cadena),
            retencion=AdaptadorRetencionPostgres(cadena),
            auditoria=AdaptadorAuditoriaPostgres(cadena),
            inventario=AdaptadorInventarioPostgres(cadena),
            roles=AdaptadorRolesPostgres(cadena),
            notificacion=notificacion,
            # `EQ-023`, hito R5 · la doble aprobación necesita algo que persista
            # entre las dos peticiones autenticadas. Ver `PuertoPropuestas`.
            propuestas=AdaptadorPropuestasPostgres(cadena),
            identidades=identidades,
            invitaciones=AdaptadorInvitacionesPostgres(
                cadena, propietarios_configurados()
            ),
        )
    except Exception as exc:  # noqa: BLE001 — el borde decide, no revienta
        faltantes.append(f"no se pudo construir el gobierno de datos (EQ-022): {exc}")
        return None


def _gobierno_sin_base(notificacion):
    """Unos repositorios cuyos puertos no responden, para registrar el router.

    Igual que `_consentimiento_sin_base()`: las rutas existen y contestan
    mantenimiento en vez de 404, porque un 404 dice «este backend no la tiene» y
    un 503 dice «la tiene y no puede atenderla», que es lo cierto.

    Recibe el MISMO canal compuesto que la rama con base (`D2`): sin él, un
    despliegue sin `AGENTE_BD` habría vuelto a construir su propia instancia.
    """
    from adaptadores.entrantes.http.rutas import gobierno as rutas_g  # noqa: PLC0415
    from adaptadores.salientes.registro.gobierno_db import (  # noqa: PLC0415
        AdaptadorAuditoriaPostgres,
        AdaptadorPropuestasPostgres,
        AdaptadorRetencionPostgres,
        AdaptadorSolicitudesDeSupresionPostgres,
    )
    from adaptadores.salientes.registro.inventario_db import (  # noqa: PLC0415
        AdaptadorInventarioPostgres,
    )
    from adaptadores.salientes.registro.invitaciones_db import (  # noqa: PLC0415
        AdaptadorInvitacionesPostgres,
    )
    from adaptadores.salientes.registro.roles_db import (  # noqa: PLC0415
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
    """El vigilante de `EQ-024`, o `None` si no hay nada que sondear (`D2-B`).

    Se compone con lo que ya existe: la cadena de `AGENTE_BD`, el `conectar()`
    con el plazo de `T-01` y **el mismo canal** que avisa al titular. Ni una
    segunda variable de entorno, ni una segunda forma de conectarse.

    `None` y no un monitor inerte: sin `AGENTE_BD` no hay base que vigilar, y una
    tarea que sondeara una cadena vacía cada treinta segundos produciría siempre
    el mismo fallo y, a los dos minutos, una alerta de una caída que no existe.
    `GET /api/salud` lo declara con `configurado: false`.

    ⚠️ **Sin destino operativo el monitor sí se crea.** Vigilar y avisar son dos
    cosas: sin `CORREO_PRIVACIDAD` la alerta no sale —y `canal.py` ya declaró esa
    carencia—, pero el estado de la base se sigue observando y publicando, que es
    lo que `/api/salud` necesita para decir la verdad.
    """
    from adaptadores.salientes.disponibilidad.postgres import (  # noqa: PLC0415
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
        TrabajosRelecturaPostgres,  # noqa: PLC0415
    )

    return TrabajosRelecturaPostgres(os.environ.get("AGENTE_BD", ""))


def crear_aplicacion() -> FastAPI:
    # `D2-B` · el canal y el monitor se componen ANTES que la aplicación porque
    # el ciclo de vida oficial de FastAPI se declara al construirla. Lo que sigue
    # —`faltantes_almacenes`— es la misma lista de siempre: `/api/salud` la
    # recibe por referencia y la lee en cada petición, así que da igual que los
    # constructores de más abajo le sigan añadiendo líneas.
    faltantes_almacenes: list[str] = []
    # `D2` · UN canal de avisos, compuesto una vez y repartido a las tres
    # familias que notifican —decisión conjunta, supresión y el monitor de
    # disponibilidad—. Dos instancias serían dos configuraciones capaces de
    # discrepar dentro del mismo proceso, y la discrepancia se vería como «a
    # unos les llega el correo y a otros no».
    canal = componer_canal()
    faltantes_almacenes.extend(canal.faltantes())
    monitor = _monitor_de_disponibilidad(canal, faltantes_almacenes)

    @asynccontextmanager
    async def ciclo_de_vida(_app: FastAPI):
        """El sondeo vive lo que vive el proceso, ni un segundo más.

        El ciclo oficial de FastAPI y no un hilo suelto: al apagar hay que
        **esperar** a que la tarea termine, y un hilo sin dueño no se puede
        esperar. `vigilancia()` cancela y aguarda; sin `AGENTE_BD` no crea nada.
        """
        from adaptadores.salientes.disponibilidad.postgres import (  # noqa: PLC0415
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
    # `PM-B11`: `composicion.py` ya construye el adaptador del perfil
    # versionado para el filtro 3 (`PM-B10`, enganchado el 2026-08-12) — se
    # reutiliza aquí para `RP-19` en vez de abrir una segunda conexión con el
    # mismo criterio (`_perfil()` y `_recuperacion()` comparten `AGENTE_BD`).
    adaptador_perfil = composicion.adaptador_perfil
    # `DD-13`: el banco es CONTENIDO versionado, así que se lee del árbol una
    # vez al arrancar. No depende de `AGENTE_BD` ni de ningún proveedor: si el
    # resto de la composición se queda sin piezas, los conceptos siguen ahí.
    #
    # ⚠️ SE CONSTRUYE AQUÍ Y NO MÁS ABAJO. Hasta `D-28` se creaba después del
    # adaptador, porque su único consumidor era la ruta `/api/conceptos`. Ahora
    # el turno también lo necesita —para decir qué páginas toca el nodo que
    # citó— y son UN objeto con dos consumidores, igual que `adaptador_perfil`
    # y `plantillas`. Construir un segundo banco leería el árbol dos veces y
    # abriría la puerta a que los dos dijeran cosas distintas.
    contenido = Path(__file__).resolve().parents[3] / "contenido"
    banco = BancoDeConceptos(contenido / "conceptos")
    # Fase 5 · la biblioteca de fuentes. Mismo criterio que el banco: contenido
    # versionado, leído una vez del árbol, sin depender de `AGENTE_BD` ni del
    # proveedor. Su informe de construcción no se pierde — lo publica
    # `/api/salud` como una degradación más, porque un catálogo que no se pudo
    # leer deja la biblioteca vacía y eso el operador tiene que verlo.
    catalogo_de_fuentes = CatalogoDeFuentes.desde_directorio(contenido / "corpus")
    faltantes_almacenes.extend(
        f"biblioteca de fuentes: {f}" for f in catalogo_de_fuentes.informe.fallos
    )

    adaptador = AdaptadorTurno(
        composicion.orquestador,
        contexto_reforzado=composicion.contexto_reforzado,
        continuidad=composicion.continuidad,
        adaptador_perfil=adaptador_perfil,
        # `PM-B28`: el mismo cargador que el filtro 7 usa para el andamiaje y
        # el 6.75 para clasificar. Un solo objeto, tres consumidores — igual
        # que `adaptador_perfil`.
        plantillas=composicion.plantillas,
        # `D-28` · de dónde salen los conceptos del §6.bis, y Fase 5 · de
        # dónde sale el rótulo legible de cada pieza de material.
        contenido=ContenidoDelCurso(banco=banco, catalogo=catalogo_de_fuentes),
    )

    sesiones = Sesiones()
    # `PM-B23`: cada turno gasta saldo del proveedor de generación. Sin tope,
    # un cliente en bucle vacía el presupuesto en una tarde. Ver limitador.py.
    limitador = LimitadorDePeticiones()
    # `PM-B24`: los almacenes del árbol del docente. Desde el 2026-08-22,
    # `Clases`/`ColaDeRevision`/`RegistroDeDocentes` (solo la mitad de
    # solicitudes) tienen un adaptador de Postgres hermano — `_clases_almacen()`
    # y compañía eligen cuál según `AGENTE_BD`, mismo criterio que
    # `composicion.py::_perfil()`. `Sesiones` sigue siendo memoria pura a
    # propósito: `RP-02` pide conservar el identificador durante la sesión,
    # no entre despliegues — ver `sesiones.py`.
    clases_almacen = _clases_almacen(faltantes_almacenes)
    analitica_docente = _analitica_docente(faltantes_almacenes)
    # Fase 8 · UNA instancia para los cuatro puntos canónicos y para la API de
    # eventos de interfaz, por el mismo motivo que la custodia privada: dos
    # construcciones serían dos lecturas del entorno capaces de discrepar.
    telemetria = _telemetria(faltantes_almacenes)
    instrumentador = Instrumentador(telemetria, _version_del_corpus())
    calculo_kpi = _calculo_kpi(faltantes_almacenes)
    auditor_informes = _auditor_informes()
    consumo_ia = _consumo_ia(faltantes_almacenes)
    reportes = _reportes(faltantes_almacenes)
    preferencias_notificacion = _preferencias_notificacion(faltantes_almacenes)
    cola = _cola_revision(faltantes_almacenes)
    registro_docentes = _registro_docentes(faltantes_almacenes)
    # Fase 2 · sesión 3 · el consentimiento deja de resolver la base por su
    # cuenta al importarse. Ver `_consentimiento_almacen()` sobre por qué este
    # no aporta una línea a `faltantes`.
    consentimiento_almacen = _consentimiento_almacen()
    # `B1` · el registro persistente de identidad. Sin él no se abre ninguna
    # sesión: ver `_identidades()` y `rutas/sesion.py::_persistir_identidad()`.
    identidades = _identidades(faltantes_almacenes)
    # `D3` · la custodia privada, compuesta UNA vez para toda la aplicación.
    #
    # Va aquí arriba, junto al canal y a los almacenes, y no dentro de
    # `_repositorios_de_consentimiento()`, porque la consumen tres sitios: el
    # recorrido del titular que carga la evidencia, la consola del revisor que
    # la lee y `GET /api/salud`, que declara si existe. Tres construcciones
    # habrían sido tres lecturas del entorno capaces de discrepar — el mismo
    # defecto que `D2` cerró con el canal de avisos.
    #
    # Se compone **siempre**, con base o sin ella: que haya custodia no depende
    # de `AGENTE_BD`.
    almacenamiento_privado = _almacenamiento_privado(faltantes_almacenes)
    # Foto de perfil: custodia distinta de las autorizaciones firmadas. La
    # referencia vive en `persona`; los bytes nunca se sirven desde Caddy.
    fotos_perfil = AlmacenFotosPerfil.desde_entorno()
    if not fotos_perfil.configurado:
        faltantes_almacenes.append("FOTOS_PERFIL_RUTA no apunta a una custodia privada escribible")
    # `B2` · la frontera versionada completa. Sin base, todos son `None` y las
    # rutas responden mantenimiento: `EQ-024` prohíbe el éxito simulado.
    consentimiento_b2 = _repositorios_de_consentimiento(
        identidades, faltantes_almacenes, canal.puerto, almacenamiento_privado
    )
    # `C2A` · la consola del revisor consume DOS de esos siete puertos, y se
    # resuelve una sola vez para que no pueda quedarse con una composición
    # distinta de la del recorrido del titular: si aquí se llamara otra vez a
    # `_consentimiento_sin_base()`, las dos familias hablarían con adaptadores
    # distintos y una podría responder mantenimiento mientras la otra no.
    repos_b2 = consentimiento_b2 or _consentimiento_sin_base(canal.puerto, almacenamiento_privado)
    # `C2` · el gobierno se compone **antes** del bucle porque su
    # `PuertoAsignacionDeRoles` lo consumen ahora dos familias: sus propias rutas
    # y `POST /api/sesion/google`, que decide con él si esta cuenta se presenta
    # como investigadora (`EQ-023`).
    #
    # Un adaptador y no dos: construir un `AdaptadorRolesPostgres` aparte para la
    # sesión habría dejado dos lecturas de `rol_asignacion` capaces de discrepar
    # el día que una cambie de criterio, y la discrepancia se vería como «el API
    # me deja y la pantalla no» — exactamente la contradicción que esta tanda
    # viene a cerrar.
    #
    # Sin base, `_gobierno_sin_base()` trae un adaptador con cadena vacía: su
    # primera consulta levanta `AlmacenNoConfigurado` y el login responde
    # mantenimiento. Falla cerrado sin ninguna rama especial.
    repos_gobierno = _repositorios_de_gobierno(
        faltantes_almacenes, canal.puerto, identidades
    ) or _gobierno_sin_base(canal.puerto)

    # `EQ-022` · la puerta de supresión, UNA y compartida por todas las familias
    # que la necesitan. Se compone sobre el puerto de estado vigente que ya
    # existe: no abre una conexión propia, no copia la consulta SQL y no vive en
    # ningún estado global.
    #
    # Sin base, `repos_b2` es el de cadena vacía y la puerta responde
    # mantenimiento en cada llamada. Falla cerrada, que es lo correcto: «no puedo
    # comprobar si hay un trámite» no puede resolverse dejando escribir.
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
            # `D3` · el MISMO adaptador que reciben el recorrido del titular y
            # la consola del revisor. La salud declara lo que la aplicación
            # tiene compuesto, no lo que el entorno diría si se releyera.
            almacenamiento=almacenamiento_privado,
            versiones=consentimiento_b2.versiones if consentimiento_b2 else None,
        ),
        rutas_sesion.crear_router(
            sesiones,
            registro_docentes,
            consentimiento_almacen,
            identidades,
            # `EQ-023` · el mismo adaptador que gobierno. Ver `repos_gobierno`.
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
                # `B2` · quien autoriza el tutor. Ver `rechazo_previo()`.
                estado_vigente=(consentimiento_b2.estado_vigente if consentimiento_b2 else None),
                instrumentador=instrumentador,
            )
        ),
        # `EQ-022` · las tres familias reciben la puerta. Quien tiene su propio
        # trámite abierto no usa el producto, y eso incluye revisar la cola,
        # crear clases y pedir o resolver el rol docente.
        rutas_supervision.crear_router(
            sesiones, cola, puerta_supresion, clases_almacen, instrumentador
        ),
        rutas_clases.crear_router(
            sesiones, clases_almacen, puerta_supresion, fotos_perfil, canal.puerto,
            preferencias_notificacion,
            correo_investigacion=canal.destino_investigacion,
        ),
        rutas_rol_docente.crear_router(sesiones, registro_docentes, puerta_supresion),
        # `R2` · consultar y exportar. Los dos `DELETE` están retirados y este
        # router no recibe adaptadores de supresión: no puede iniciar una cascada.
        # Las preferencias de interfaz se consultan sólo para la exportación propia.
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
        # Fase 5 · `EQ-013`. Públicas como las de conceptos y por el mismo
        # motivo: son material del curso. La autorización por obra la aplica
        # cada ruta contra `FUENTES.md`, no el cliente. La sesión limita el
        # material al piloto institucional autenticado.
        rutas_fuentes.crear_router(catalogo_de_fuentes, sesiones),
        # `B2` · el recorrido de onboarding, consentimiento versionado y
        # evidencia. Se registra siempre para que sus rutas existan y respondan
        # mantenimiento: si el router desapareciera sin base, el cliente vería
        # 404 y no sabría distinguir «no configurado» de «esta versión del
        # backend no lo tiene».
        rutas_consentimiento.crear_router(sesiones, repos_b2),
        # `C2A` · la cola paginada, el detalle y el archivo, para quien tiene el
        # rol de `EQ-023`. Mismo criterio que arriba: se registra siempre, de
        # modo que sin base responda mantenimiento y no 404. Recibe dos puertos
        # y no los siete — ver `DependenciasDeEvidencias`.
        rutas_evidencias.crear_router(
            sesiones,
            rutas_evidencias.DependenciasDeEvidencias(
                evidencias=repos_b2.evidencias,
                almacenamiento=repos_b2.almacenamiento,
            ),
            # La MISMA puerta compuesta arriba, no otra: una segunda instancia
            # sería una segunda consulta y, el día que alguna cambiara, dos
            # respuestas distintas a la misma pregunta.
            puerta_supresion,
        ),
        #  · supresión solicitada, retención e inventario de cascada. Mismo
        # criterio: el router se registra siempre y responde mantenimiento.
        # La puerta NO cubre consultar ni cancelar el trámite —son justo los
        # derechos que `EQ-022` conserva— sino proponer retención, aprobar
        # propuestas y gobernar roles.
        rutas_gobierno.crear_router(sesiones, repos_gobierno, puerta_supresion),
        # Comunicación saliente iniciada por un investigador. El router recibe
        # el mismo canal y la misma auditoría del gobierno de datos: no crea una
        # segunda configuración ni permite enviar antes de registrar el intento.
        rutas_correos.crear_router(
            sesiones,
            canal.puerto,
            repos_gobierno.auditoria,
            puerta_supresion,
            canal_configurado=canal.envia,
        ),
        rutas_reportes.crear_router(sesiones, reportes, puerta_supresion),
        # `PM-B37` · el historial de conversación. Exige sesión AUTENTICADA
        # (`D-30`) y su contrato es el de `08-Contrato-del-Turno.md` §13, que es la
        # frontera con el
        # sidebar de `PM-F20`.
        # Fase 5 · el mismo catálogo que el turno en vivo, para que «Material
        # del curso» se llame igual en la respuesta y en el hilo.
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
        # Fase 8 · el contrato de los eventos que sólo ocurren en el navegador.
        # Se registra siempre, igual que consentimiento y evidencias: sin base
        # responde mantenimiento, y no 404, para que el cliente distinga «no
        # configurado» de «esta versión del backend no lo tiene».
        rutas_telemetria.crear_router(sesiones, telemetria, puerta_supresion),
        # Fase 8 · el catálogo y su cálculo. Las cuatro rutas se registran
        # siempre: sin base responden mantenimiento, no 404. Quién puede pedir
        # qué lo deciden dos barreras —el catálogo por alcance y el adaptador
        # dentro de la transacción—, y las dos están en sus módulos.
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
        """`M1` · el valor no era representable, así que la operación no ocurrió.

        Una sola red para todas las rutas, y no un `except` por ruta. `M1` sólo
        obligaba a corregir `GET /api/consentimiento/version/{codigo}/texto`,
        pero el desenlace nuevo lo puede levantar **cualquier** ruta que pase un
        identificador del cliente a la base —clases, conceptos, evidencias,
        gobierno, historial, supervisión—. Sin esto, las cuarenta que capturan
        `(AlmacenNoConfigurado, AlmacenNoDisponible)` lo dejarían escapar y un
        `\\x00` pasaría de responder 503 a responder 500: cambiar un error de
        clasificación por uno peor.

        **400 y no 404**, al revés que la ruta del documento. Aquí no se sabe si
        el valor era un identificador o un campo del cuerpo, y un 404 genérico
        afirmaría que algo no existe sin haberlo buscado. La ruta del texto sí
        lo sabe —su parámetro es una clave de búsqueda— y por eso lo estrecha a
        404 en su propio `except`, con el mismo cuerpo que un código
        desconocido.

        No dice qué valor era ni por qué: quien mandó un NUL no necesita que se
        lo confirmen.
        """
        return JSONResponse(
            {"detalle": "la petición contiene un valor que no se puede procesar"},
            status_code=400,
        )

    return app


#: Lo que `uvicorn adaptadores.entrantes.http.aplicacion:app` necesita.
app = crear_aplicacion()
