from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from dominio.filtros.arbitraje import FiltroArbitraje
from dominio.filtros.deteccion import FiltroDeteccion
from dominio.filtros.diagnostico import FiltroDiagnostico
from dominio.filtros.enrutamiento import FiltroEnrutamiento
from dominio.filtros.estrategia import FiltroEstrategia
from dominio.filtros.generacion import FiltroGeneracion
from dominio.filtros.intencion import FiltroIntencion
from dominio.filtros.intento import FiltroIntento
from dominio.filtros.juez import FiltroJuez
from dominio.filtros.normalizacion import FiltroNormalizacion
from dominio.filtros.precomputo import FiltroPrecomputo
from dominio.filtros.prompt import FiltroPrompt
from dominio.filtros.recuperacion import FiltroRecuperacion
from dominio.filtros.registro import FiltroRegistro
from dominio.filtros.sondeo import FiltroSondeo
from dominio.filtros.verificacion import FiltroVerificacion
from dominio.orquestador import Orquestador
from dominio.puertos.corpus import Recuperacion
from dominio.puertos.plantillas import PuertoPlantillas

if TYPE_CHECKING:
    from adaptadores.salientes.registro.archivo import AdaptadorRegistroArchivo
    from adaptadores.salientes.registro.historial import AdaptadorHistorialPostgres
    from adaptadores.salientes.registro.postgres import AdaptadorPerfilPostgres

@dataclass(frozen=True)
class Composicion:

    orquestador: Orquestador
    faltantes: tuple[str, ...]
    contexto_reforzado: bool = False
    continuidad: bool = False
    interpretacion: str = "desactivada"
    retroalimentacion_directa: bool = False
    factores_conductuales: bool = False

    adaptador_perfil: AdaptadorPerfilPostgres | None = None

    plantillas: PuertoPlantillas | None = None

    adaptador_registro_turno: AdaptadorRegistroArchivo | None = None

    adaptador_historial: AdaptadorHistorialPostgres | None = None
    configuracion_sondeos: object | None = None

class _CorpusVacio:

    def recuperar(self, consulta: str, nodo: str | None = None, k: int = 3) -> Recuperacion:
        return Recuperacion(fragmentos=(), similitudes=(), sin_fuente=True)

class _SinIdentificador:

    def identificar_nodo(self, consulta: str) -> str | None:
        return None

class _IndiceVacio:

    def buscar(self, consulta: str, k: int = 3, nodo: str | None = None):
        return []

def _grafo_y_perfil(raiz: Path):
    from adaptadores.salientes.corpus.cargador import (
        cargar,
        claves_de_obra,
    )
    from adaptadores.salientes.recuperacion import (
        GrafoEnMemoria,
        PerfilLexico,
    )

    contenido = raiz / "contenido"
    grafo = GrafoEnMemoria.desde_archivo(contenido / "grafo" / "grafo.json")
    corpus_dir = contenido / "corpus"
    cargado = cargar(
        corpus_dir / "fragmentos", obras=claves_de_obra(corpus_dir / "fuentes.json")
    )
    return grafo, PerfilLexico.desde_fragmentos(cargado.fragmentos)

def _identificador_local(raiz: Path, faltantes: list[str]):
    try:
        from adaptadores.salientes.recuperacion import (
            RecuperadorJerarquico,
        )

        grafo, perfil = _grafo_y_perfil(raiz)
        return RecuperadorJerarquico(_IndiceVacio(), grafo, perfil=perfil)
    except Exception as exc:
        faltantes.append(
            f"no se pudo levantar el enrutamiento por nodo sin índice: {exc}"
        )
        return _SinIdentificador()

def _recuperacion(raiz: Path, faltantes: list[str], cadena: str):
    local = _identificador_local(raiz, faltantes)

    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: sin índice, los turnos van en "
            "modo sin fuente (ADR-006 U3). El enrutamiento por nodo sí sigue "
            "activo: no depende de la base"
        )
        return local, _CorpusVacio()

    try:
        from adaptadores.salientes.recuperacion import (
            IndicePostgres,
            RecuperadorJerarquico,
        )
        from adaptadores.salientes.recuperacion import (
            codificador as _codificador,
        )

        grafo, perfil = _grafo_y_perfil(raiz)
        recuperador = RecuperadorJerarquico(
            IndicePostgres(cadena, _codificador.CodificadorE5()), grafo, perfil=perfil
        )

        return recuperador, recuperador
    except Exception as exc:

        faltantes.append(
            f"recuperación semántica degradada: no se pudo levantar el índice "
            f"ni el encoder E5 ({exc}). Los turnos van en modo sin fuente "
            f"(ADR-006 U3); el enrutamiento por nodo sigue activo"
        )
        return local, _CorpusVacio()

def _generador(faltantes: list[str], cadena: str):
    cual = os.environ.get("AGENTE_LLM", "").strip().lower()
    if not cual:
        faltantes.append(
            "AGENTE_LLM no está en el entorno (ollama | deepseek): sin "
            "generador, el turno se degrada en el filtro 8"
        )
        return None
    try:
        registrador = None
        if cadena:
            from adaptadores.salientes.registro.consumo_ia_db import (
                AdaptadorConsumoIAPostgres,
            )

            registrador = AdaptadorConsumoIAPostgres(cadena)
        else:
            faltantes.append(
                "AGENTE_BD no está en el entorno: las llamadas al proveedor no tendrán "
                "medición institucional de consumo ni costo"
            )
        if cual == "ollama":
            from adaptadores.salientes.generacion.ollama import (
                AdaptadorOllama,
            )

            return AdaptadorOllama(registrador_consumo=registrador)
        if cual == "deepseek":
            from adaptadores.salientes.generacion.deepseek import (
                AdaptadorDeepSeek,
            )

            return AdaptadorDeepSeek(registrador_consumo=registrador)
    except Exception as exc:
        faltantes.append(f"no se pudo construir el generador «{cual}»: {exc}")
        return None

    faltantes.append(f"AGENTE_LLM=«{cual}» no es un proveedor conocido")
    return None

def _plantillas(raiz: Path, faltantes: list[str]):
    try:
        from adaptadores.salientes.plantillas import (
            CargadorDePlantillas,
        )

        cargador = CargadorDePlantillas(raiz / "contenido" / "plantillas")
    except Exception as exc:
        faltantes.append(f"no se pudieron leer las plantillas socráticas (PM-C14): {exc}")
        return None

    secuencias, genericas = cargador.cuantas
    if not secuencias and not genericas:
        faltantes.append(
            "contenido/plantillas/ está vacío o no existe: el filtro 7 vuelve al "
            "andamio genérico y la pedagogía de PM-C14 no llega al generador"
        )

    for problema in cargador.problemas:
        faltantes.append(f"contenido/plantillas/{problema}")
    return cargador

def _perfil(faltantes: list[str], cadena: str):
    if not cadena:

        faltantes.append(
            "AGENTE_BD no está en el entorno: el perfil versionado (PM-B11) no "
            "se carga ni se guarda, y la cascada de supresión de RD-22 no lo "
            "alcanza"
        )
        return None
    try:
        from adaptadores.salientes.registro.postgres import (
            AdaptadorPerfilPostgres,
        )

        return AdaptadorPerfilPostgres(cadena)
    except Exception as exc:
        faltantes.append(f"no se pudo construir el adaptador de perfil (PM-B11): {exc}")
        return None

def _historial(faltantes: list[str], cadena: str):
    if not cadena:
        faltantes.append(
            "AGENTE_BD no está en el entorno: el historial de conversación "
            "(PM-B37) no se escribe ni se puede consultar, y la cascada de "
            "supresión de RD-22 no lo alcanza"
        )
        return None
    try:
        from adaptadores.salientes.registro.historial import (
            AdaptadorHistorialPostgres,
        )

        return AdaptadorHistorialPostgres(cadena)
    except Exception as exc:
        faltantes.append(f"no se pudo construir el historial (PM-B37): {exc}")
        return None

def _registro_turno(raiz: Path, faltantes: list[str], cadena: str):
    if not cadena:

        faltantes.append(
            "AGENTE_BD no está en el entorno: el registro del turno (DD-08) no "
            "se escribe, el filtro 12 no entra en la cadena, y la cascada de "
            "supresión de RD-22 no lo alcanza"
        )
        return None
    try:
        from adaptadores.salientes.registro.archivo import (
            AdaptadorRegistroArchivo,
        )

        return AdaptadorRegistroArchivo(cadena, raiz / "infraestructura" / "registro_turnos")
    except Exception as exc:
        faltantes.append(f"no se pudo construir el registro de turnos (DD-08): {exc}")
        return None

def _filtros_de_interpretacion(interprete, solo_observar):
    if interprete is None:
        return []
    from dominio.filtros.interpretacion import FiltroInterpretacion

    return [FiltroInterpretacion(interprete, observar=solo_observar)]

def _interpretacion_del_entorno():
    modo = os.environ.get("AGENTE_INTERPRETACION", "desactivada")
    if modo == "desactivada":
        return None, False
    if modo not in ("corroboracion", "observacion"):
        raise ValueError("AGENTE_INTERPRETACION debe ser desactivada, corroboracion u observacion")
    from adaptadores.salientes.generacion.interpretacion_deepseek import (
        InterpretacionDeepSeek,
    )

    factores = os.environ.get("AGENTE_FACTORES_CONDUCTUALES", "0") == "1"
    return InterpretacionDeepSeek(factores_conductuales=factores), modo == "observacion"

def _filtros_de_retroalimentacion(simbolico, habilitada):
    if not habilitada:
        return []
    from dominio.filtros.retroalimentacion import FiltroRetroalimentacion

    return [FiltroRetroalimentacion(simbolico)]

def _verificador(simbolico, retroalimentacion):
    if not retroalimentacion:
        return FiltroVerificacion(simbolico)
    from dominio.filtros.verificacion_retroalimentacion import (
        FiltroVerificacionRetroalimentacion,
    )

    return FiltroVerificacionRetroalimentacion(simbolico)

@dataclass(frozen=True)
class ModoExperimental:
    interprete: object | None = None
    observar: bool = False
    retroalimentacion_directa: bool = False
    filtros_antes_interpretacion: tuple = ()
    filtros_despues_prompt: tuple = ()
    contexto_reforzado: bool = False
    continuidad: bool = False

def componer(
    raiz: Path | None = None, generador=None, cadena_bd: str | None = None,
    *, experimento: ModoExperimental | None = None, filtros_adicionales: tuple = (),
) -> Composicion:

    raiz = raiz or Path(__file__).resolve().parents[3]

    if experimento is None and generador is None:
        interprete, solo_observar_interpretacion = _interpretacion_del_entorno()
        retroalimentacion_directa = generador is None and os.environ.get("AGENTE_RETROALIMENTACION_DIRECTA") == "1"
        modo_contexto = os.environ.get("AGENTE_CONTEXTO_CONVERSACIONAL", "actual")
        if modo_contexto not in ("actual", "reforzado"):
            raise ValueError("AGENTE_CONTEXTO_CONVERSACIONAL debe ser actual o reforzado")
        contexto_reforzado = modo_contexto == "reforzado"
    else:
        experimento = experimento or ModoExperimental()
        interprete = experimento.interprete
        solo_observar_interpretacion = experimento.observar
        retroalimentacion_directa = experimento.retroalimentacion_directa
        contexto_reforzado = experimento.contexto_reforzado
    from adaptadores.entrantes.http.contexto_conversacional import (
        FiltroContextoEntrada,
        FiltroContextoPrompt,
    )
    faltantes: list[str] = []

    cadena = os.environ.get("AGENTE_BD", "") if cadena_bd is None else cadena_bd

    identificador, corpus = _recuperacion(raiz, faltantes, cadena)

    if generador is None:
        generador = _generador(faltantes, cadena)
    adaptador_perfil = _perfil(faltantes, cadena)
    adaptador_registro_turno = _registro_turno(raiz, faltantes, cadena)
    adaptador_historial = _historial(faltantes, cadena)
    plantillas = _plantillas(raiz, faltantes)
    configuracion_sondeos = None
    if cadena:
        from adaptadores.salientes.registro.configuracion_sondeos_db import (
            AdaptadorConfiguracionSondeosPostgres,
        )
        configuracion_sondeos = AdaptadorConfiguracionSondeosPostgres(cadena)

    from adaptadores.salientes.simbolico.adaptador import (
        AdaptadorSimbolico,
    )

    simbolico = AdaptadorSimbolico()
    continuidad = os.environ.get("AGENTE_CONTINUIDAD_TUTOR") == "1" if experimento is None else experimento.continuidad
    if continuidad:
        from adaptadores.salientes.simbolico.proceso_aislado import SimbolicoAislado
        simbolico = SimbolicoAislado(simbolico)
    from dominio.filtros.continuidad import (
        FiltroContinuidadEntrada,
        FiltroContinuidadObjetivo,
        FiltroContinuidadPrompt,
        FiltroContinuidadResolver,
        FiltroContinuidadSalida,
    )

    filtros = [
        FiltroNormalizacion(),
        *([FiltroContinuidadEntrada()] if continuidad else []),
        FiltroIntencion(),
        *([FiltroContextoEntrada()] if contexto_reforzado else []),
        *(experimento.filtros_antes_interpretacion if experimento else ()),
        *(_filtros_de_interpretacion(interprete, solo_observar_interpretacion)),
        *([FiltroContinuidadResolver()] if continuidad else []),

        FiltroDeteccion(),

        FiltroEnrutamiento(identificador, plantillas),
        FiltroRecuperacion(corpus),

        FiltroArbitraje(),

        FiltroPrecomputo(simbolico),

        FiltroIntento(simbolico),
        *_filtros_de_retroalimentacion(simbolico, retroalimentacion_directa),

        FiltroDiagnostico(plantillas, simbolico),

        FiltroSondeo(plantillas, configuracion_sondeos),

        FiltroEstrategia(),
        *([FiltroContinuidadObjetivo(simbolico)] if continuidad else []),

        FiltroPrompt(plantillas),
        *([FiltroContextoPrompt()] if contexto_reforzado else []),
        *([FiltroContinuidadPrompt()] if continuidad else []),
        *(experimento.filtros_despues_prompt if experimento else ()),
    ]
    if generador is not None:

        maximo = int(os.environ.get("AGENTE_MAX_UNIDADES", "4096"))
        filtros.append(FiltroGeneracion(generador, maximo_de_unidades=maximo))
        if continuidad:
            from dominio.filtros.reparacion_formato import FiltroReparacionFormato

            filtros.append(FiltroReparacionFormato(generador, maximo_de_unidades=maximo, cas=simbolico))
    filtros += [

        _verificador(simbolico, retroalimentacion_directa),
        *([FiltroContinuidadSalida(simbolico)] if continuidad else []),
        FiltroJuez(),
    ]
    if adaptador_registro_turno is not None:

        from adaptadores.salientes.registro.factores_db import (
            AdaptadorFactoresPostgres,
        )

        factores = AdaptadorFactoresPostgres(cadena) if cadena and os.environ.get("AGENTE_FACTORES_CONDUCTUALES", "0") == "1" else None
        filtros.append(FiltroRegistro(adaptador_registro_turno, adaptador_historial, factores))

    filtros.extend(filtros_adicionales)
    return Composicion(
        orquestador=Orquestador(filtros),
        faltantes=tuple(faltantes),
        adaptador_perfil=adaptador_perfil,
        plantillas=plantillas,
        adaptador_registro_turno=adaptador_registro_turno,
        adaptador_historial=adaptador_historial,
        configuracion_sondeos=configuracion_sondeos,
        contexto_reforzado=contexto_reforzado,
        continuidad=continuidad,
        interpretacion=("desactivada" if interprete is None else
                        "observacion" if solo_observar_interpretacion else "corroboracion"),
        retroalimentacion_directa=retroalimentacion_directa,
        factores_conductuales=bool(getattr(interprete, "factores_conductuales", False)),
    )
