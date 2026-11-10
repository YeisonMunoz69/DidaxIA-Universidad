"""
consentimiento_versionado_db.py — Versiones y eventos contra la migración 11
==============================================================================

Las dos implementaciones PostgreSQL de la frontera nueva del consentimiento:
`AdaptadorVersionesDeConsentimientoPostgres` sobre `consentimiento_version` y
`AdaptadorEventosDeConsentimientoPostgres` sobre `consentimiento_evento`.

⚠️ **No sustituyen a `consentimiento_db.py`.** Aquel sigue siendo el que las
rutas HTTP consumen, sigue escribiendo en `consentimiento_usuario` y no se ha
tocado. Estos dos escriben en tablas nuevas que hoy nadie más lee. La sesión 3
decide cuándo cambia el borde; hasta entonces conviven sin mezclarse, y ninguna
fila pasa de una tabla a la otra.

Lo que este archivo NO hace, y es su razón de ser
-----------------------------------------------------------
- **No hay `ON CONFLICT` sobre eventos.** `registrar()` es un `INSERT` a secas;
  no existe ninguna clave única por sujeto que pudiera convertirlo en un
  `UPDATE`, así que un rechazo anterior sigue ahí después de reaceptar.
- **No hay `UPDATE` ni `DELETE`** en toda la clase de eventos.
- **No se captura la excepción para devolver `None`.** Un fallo del almacén
  levanta, y por eso `consultar_version()` devolviendo `None` significa una sola
  cosa: ese código no existe.

La transición se comprueba dentro de la transacción
--------------------------------------------------------------
`registrar()` bloquea la fila de la persona, lee el estado vigente y decide, todo
en la misma transacción. Comprobarlo fuera dejaría una ventana en la que dos
peticiones simultáneas leen `otorgado` y escriben dos revocaciones — o peor, una
revocación y una reaceptación cuyo orden final nadie eligió.


"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_categoria_de_edad,
    exigir_persona,
    exigir_sin_supresion,
    exigir_version_de_la_concesion,
    exigir_version_requerida,
    insertar_acto,
    ultimo_acto,
    version_de_la_concesion_de,
    version_requerida_de,
)
from dominio.modelo.consentimiento import (
    Alcance,
    EstadoConsentimiento,
    EventoConsentimiento,
    Finalidad,
    HistorialDeConsentimiento,
    VersionDeConsentimiento,
    exigir_transicion,
)
from dominio.modelo.identidad import CategoriaDeEdad
from dominio.modelo.instantanea_consentimiento import (
    InstantaneaDeVersion,
    PublicacionDeVersion,
)
from dominio.puertos.almacen import EscrituraRechazada
from dominio.puertos.instantaneas import ResultadoDePublicacion


class AdaptadorVersionesDeConsentimientoPostgres(RepositorioPostgres):
    """`PuertoVersionesDeConsentimiento` sobre `consentimiento_version` y su
    tabla de finalidades.

    ⚠️ La tabla nace y sigue **vacía** en este árbol: el texto final del
    consentimiento es una decisión abierta del equipo. Este adaptador existe para
    el día que la haya, no para inventar una.
    """

    def registrar_version(self, version: VersionDeConsentimiento) -> None:
        """Publica la versión y sus finalidades en una sola transacción.

        Una versión publicada no se reescribe: su huella es la prueba de qué
        texto leyó quien la aceptó. Un código repetido es `EscrituraRechazada`, no
        una actualización silenciosa.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM consentimiento_version WHERE codigo = %s",
                (version.codigo,),
            )
            if cur.fetchone() is not None:
                raise EscrituraRechazada(
                    "esa versión ya está publicada; una corrección es una versión nueva"
                )
            cur.execute(
                """
                INSERT INTO consentimiento_version
                    (codigo, alcance, huella_contenido, vigente_desde, vigente_hasta)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    version.codigo,
                    version.alcance.value,
                    version.huella_contenido,
                    version.vigente_desde,
                    version.vigente_hasta,
                ),
            )
            cur.executemany(
                """
                INSERT INTO consentimiento_version_finalidad (version, finalidad)
                VALUES (%s, %s)
                """,
                [(version.codigo, f.value) for f in sorted(version.finalidades)],
            )

    def consultar_version(self, codigo: str) -> VersionDeConsentimiento | None:
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT codigo, alcance, huella_contenido, vigente_desde, vigente_hasta
                  FROM consentimiento_version
                 WHERE codigo = %s
                """,
                (codigo,),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            return self._con_finalidades(cur, fila)

    def versiones(self, alcance: Alcance | None = None) -> tuple[VersionDeConsentimiento, ...]:
        """Todas, o las de un alcance. `vigente_desde` descendente y `codigo`
        como desempate, para que dos versiones del mismo día no cambien de orden
        entre dos consultas."""
        condicion = "WHERE alcance = %s" if alcance is not None else ""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"""
                SELECT codigo, alcance, huella_contenido, vigente_desde, vigente_hasta
                  FROM consentimiento_version
                  {condicion}
                 ORDER BY vigente_desde DESC, codigo DESC
                """,  # noqa: S608 — `condicion` es una constante de este módulo
                (alcance.value,) if alcance is not None else (),
            )
            filas = list(cur.fetchall())
            return tuple(self._con_finalidades(cur, fila) for fila in filas)

    def version_requerida(self, alcance: Alcance) -> VersionDeConsentimiento | None:
        """La que rige ahora en ese alcance, según `didaxia_version_requerida()`.

        Hoy devuelve `None` para los tres alcances en cualquier base de este
        árbol: no hay ningún texto publicado. Que eso deje el acceso en
        onboarding en vez de habilitado es exactamente lo que la revisión pidió.

        Devuelve `None` también cuando la última versión que comenzó ya venció,
        **aunque quede una anterior abierta**: publicar términos posteriores
        desplaza a los previos de forma definitiva (hito A2).
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            codigo = version_requerida_de(cur, Alcance(alcance).value)
            if codigo is None:
                return None
            cur.execute(
                """
                SELECT codigo, alcance, huella_contenido, vigente_desde, vigente_hasta
                  FROM consentimiento_version WHERE codigo = %s
                """,
                (codigo,),
            )
            return self._con_finalidades(cur, cur.fetchone())

    # -- `§8` · la version y su documento, juntos ---------------------------

    def publicar(self, publicacion: PublicacionDeVersion) -> ResultadoDePublicacion:
        """Publica una versión con su documento, en una transacción.

        Es `publicar_lote()` con un solo elemento, y se define así para que no
        haya dos redacciones de la misma escritura.
        """
        (resultado,) = self.publicar_lote((publicacion,))
        return resultado

    def publicar_lote(
        self, publicaciones: Sequence[PublicacionDeVersion]
    ) -> tuple[ResultadoDePublicacion, ...]:
        """Publica un paquete entero en **una sola** transacción · `C1-D`.

        🐛 **El defecto que esto cierra.** `publicar_consentimiento.py` recorría
        el manifiesto llamando a `publicar()` una vez por versión, y cada
        llamada abría su propia transacción. Si la primera escribía y la segunda
        colisionaba, la herramienta terminaba con **un subconjunto activo**: por
        ejemplo el consentimiento del titular publicado y el asentimiento no.

        El informe de la revisión R2 llamó «transaccional» a esa publicación, y
        sólo lo era cada versión por separado. Un paquete titular / asentimiento
        / representante se aprueba **como conjunto**: publicar la mitad deja el
        recorrido del menor a medias y, peor, deja regir un documento que nadie
        aprobó suelto.

        Y no se podía compensar desde el CLI: estas tablas son deliberadamente
        inmutables, así que lo escrito no se puede deshacer con un `DELETE`. O
        entra todo en la misma transacción, o no hay atomicidad posible.

        Semántica del lote, explícita
        ---------------------------------
        - **una entrada rechazada aborta el lote entero** y no deja ni un
          cambio: la excepción sale del `with`, y PostgreSQL revierte;
        - **repetir un lote idéntico escribe cero** y devuelve `escrita=False`
          en todas: la idempotencia de cada versión, aplicada al conjunto;
        - **un lote mixto** —algunas ya publicadas idénticas y otras nuevas—
          escribe sólo las nuevas y reconoce las que estaban. Es el caso de un
          reintento que se cortó a medias en una versión anterior de esta
          herramienta, y tiene que poder completarse.

        Concurrencia
        ----------------
        Dos publicaciones simultáneas con códigos solapados no pueden producir
        un conjunto parcial: la segunda espera en el índice único del código
        repetido y termina en error, lo que revierte **su** lote completo. La
        primera commitea entero o no commitea nada.
        """
        if not publicaciones:
            return ()
        with self._escritura() as cnx, cnx.cursor() as cur:
            return tuple(self._publicar_en(cur, p) for p in publicaciones)

    def _publicar_en(
        self, cur: Any, publicacion: PublicacionDeVersion
    ) -> ResultadoDePublicacion:
        """Una versión dentro de una transacción **ya abierta**.

        No abre ninguna: recibe el cursor para que el lote entero comparta
        transacción. Ésa es toda la diferencia con la versión anterior de este
        código, y es la que hace cierta la palabra «atómica».

        Se comprueba **dentro** de la transacción y no antes: entre una lectura
        previa y esta escritura cabe otra publicación. `FOR UPDATE` sobre la
        fila existente cierra esa ventana.

        ⚠️ La comparación del cuerpo es **byte a byte sobre la forma canónica**,
        no «parecido»: `InstantaneaDeVersion` canonicaliza al construirse, y lo
        guardado también está canonicalizado, así que una diferencia de una coma
        —o de un espacio— cuenta como documento distinto. Es lo que hace cierta
        la regla de que cambiar una coma exige una versión nueva.
        """
        instantanea = publicacion.instantanea
        cur.execute(
            """
            SELECT alcance, huella_contenido
              FROM consentimiento_version
             WHERE codigo = %s
               FOR UPDATE
            """,
            (publicacion.codigo,),
        )
        fila = cur.fetchone()
        if fila is not None:
            return self._publicacion_repetida(cur, publicacion, fila)

        cur.execute(
            """
            INSERT INTO consentimiento_version
                (codigo, alcance, huella_contenido, vigente_desde, vigente_hasta)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                publicacion.codigo,
                publicacion.alcance.value,
                publicacion.huella,
                publicacion.vigente_desde,
                publicacion.vigente_hasta,
            ),
        )
        cur.executemany(
            """
            INSERT INTO consentimiento_version_finalidad (version, finalidad)
            VALUES (%s, %s)
            """,
            [(publicacion.codigo, f.value) for f in sorted(publicacion.finalidades)],
        )
        cur.execute(
            """
            INSERT INTO consentimiento_version_texto (version, cuerpo, medio)
            VALUES (%s, %s, %s)
            """,
            (publicacion.codigo, instantanea.cuerpo, instantanea.medio),
        )
        return ResultadoDePublicacion(
            codigo=publicacion.codigo,
            escrita=True,
            motivo="versión publicada con su documento",
        )

    def _publicacion_repetida(
        self, cur: Any, publicacion: PublicacionDeVersion, fila: tuple
    ) -> ResultadoDePublicacion:
        """Que hacer cuando el codigo ya existe: repetir o detenerse.

        Nunca escribe. O reconoce que lo publicado es exactamente esto —y
        entonces no hay nada que hacer— o levanta.
        """
        alcance_guardado, huella_guardada = fila
        if alcance_guardado != publicacion.alcance.value:
            raise EscrituraRechazada(
                f"«{publicacion.codigo}» ya está publicado con alcance "
                f"«{alcance_guardado}»: un código no cambia de alcance"
            )
        if huella_guardada != publicacion.huella:
            raise EscrituraRechazada(
                f"«{publicacion.codigo}» ya está publicado con OTRA huella; no se "
                "sobrescribe: su huella es la prueba de qué texto leyó quien lo "
                "aceptó. Una corrección es una versión nueva"
            )
        cur.execute(
            "SELECT cuerpo FROM consentimiento_version_texto WHERE version = %s",
            (publicacion.codigo,),
        )
        guardado = cur.fetchone()
        if guardado is None:
            # Huella igual y sin instantanea: es una version publicada antes de
            # que esta tabla existiera. **No se rellena.** Añadirle ahora un
            # cuerpo seria afirmar que es el que leyeron quienes ya aceptaron, y
            # eso no se puede saber desde aqui: la decision es humana.
            raise EscrituraRechazada(
                f"«{publicacion.codigo}» existe sin instantánea: es anterior a "
                "esta tabla y no se le añade una a posteriori. Publique una "
                "versión nueva"
            )
        if guardado[0] != publicacion.instantanea.cuerpo:
            # Mismo codigo y misma huella con OTRO cuerpo es una colision de
            # SHA-256 o —muchisimo mas probable— un error de canonicalizacion.
            # Las dos exigen mirar, no continuar.
            raise EscrituraRechazada(
                f"«{publicacion.codigo}» tiene la misma huella y un cuerpo "
                "distinto: no se continúa"
            )
        return ResultadoDePublicacion(
            codigo=publicacion.codigo,
            escrita=False,
            motivo="ya estaba publicada, idéntica: no se escribió nada",
        )

    def instantanea_de(self, codigo: str) -> InstantaneaDeVersion | None:
        """El documento publicado bajo ese código. Lectura por código, no por ruta."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT v.codigo, v.alcance, t.cuerpo, t.medio
                  FROM consentimiento_version_texto t
                  JOIN consentimiento_version v ON v.codigo = t.version
                 WHERE t.version = %s
                """,
                (codigo,),
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            return InstantaneaDeVersion(
                codigo=fila[0], alcance=Alcance(fila[1]), cuerpo=fila[2], medio=fila[3]
            )

    def _con_finalidades(self, cur: Any, fila: tuple) -> VersionDeConsentimiento:
        codigo, alcance, huella, desde, hasta = fila
        cur.execute(
            "SELECT finalidad FROM consentimiento_version_finalidad WHERE version = %s",
            (codigo,),
        )
        finalidades = frozenset(Finalidad(f[0]) for f in cur.fetchall())
        return VersionDeConsentimiento(
            codigo=codigo,
            alcance=Alcance(alcance),
            finalidades=finalidades,
            huella_contenido=huella,
            vigente_desde=desde,
            vigente_hasta=hasta,
        )


class AdaptadorEventosDeConsentimientoPostgres(RepositorioPostgres):
    """`PuertoEventosDeConsentimiento` sobre `consentimiento_evento`."""

    def registrar(
        self,
        sujeto_google: str,
        version: str,
        estado: EstadoConsentimiento,
        comprobante: str,
    ) -> EventoConsentimiento:
        """Añade un acto. Nunca modifica ninguno anterior."""
        # Se construye antes de conectar para que un comprobante malformado o un
        # `pendiente` —que no es un acto— fallen sin tocar la base. El `momento`
        # provisional se reemplaza por el que asigna PostgreSQL.
        provisional = EventoConsentimiento(
            sujeto_google=sujeto_google,
            version=version,
            estado=estado,
            comprobante=comprobante,
            momento=datetime.now(UTC),
        )
        with self._escritura() as cnx, cnx.cursor() as cur:
            # Igual que el asentimiento: revocar es un derecho que el trámite de
            # `EQ-022` no suspende; otorgar o rechazar sueltos sí serían
            # tratamiento nuevo. Hoy sólo llega aquí la revocación —la decisión
            # la registra la conjunta— y la distinción se escribe igual para que
            # una vía futura no se estrene abierta.
            edad = exigir_persona(cur, provisional.sujeto_google)
            if provisional.estado is not EstadoConsentimiento.REVOCADO:
                exigir_sin_supresion(cur, provisional.sujeto_google)
            # La categoría se decide con la fila de `persona` ya bloqueada, y el
            # disparador la vuelve a derivar al insertar: lo que se envíe en el
            # INSERT se descarta. Aquí sirve para dos cosas que el disparador no
            # puede dar: rechazar con motivo cuando falta la edad, y saber si la
            # categoría cambió desde el último acto.
            categoria = exigir_categoria_de_edad(edad)
            # Otorgar y rechazar exigen la versión requerida; revocar retira la
            # concesión que se otorgó, aunque su texto haya vencido o haya sido
            # desplazado (hito A2). Son dos semánticas y la base las separa igual.
            if provisional.estado is EstadoConsentimiento.REVOCADO:
                exigir_version_de_la_concesion(
                    cur, "consentimiento_evento", provisional.sujeto_google, provisional.version
                )
            else:
                exigir_version_requerida(cur, provisional.version, Alcance.TITULAR.value)
            actual, version_actual, categoria_actual = self._vigente(
                cur, provisional.sujeto_google
            )
            exigir_transicion(
                actual,
                provisional.estado,
                cambia_version=version_actual != provisional.version,
                # `EQ-021`: cumplir 18 obliga a volver a pedir autorización, y esa
                # segunda aceptación llega con la MISMA versión vigente.
                cambia_categoria=(
                    categoria_actual is not None and categoria_actual is not categoria
                ),
            )
            identificador, momento, categoria_guardada = insertar_acto(
                cur,
                "consentimiento_evento",
                sujeto=provisional.sujeto_google,
                version=provisional.version,
                estado=provisional.estado.value,
                comprobante=provisional.comprobante,
            )
            return replace(
                provisional,
                momento=momento,
                secuencia=identificador,
                categoria_edad=CategoriaDeEdad(categoria_guardada),
            )


    def version_de_la_concesion(self, sujeto_google: str) -> str | None:
        """La versión de la última concesión otorgada. Ver el puerto.

        Misma consulta que `exigir_version_de_la_concesion()` usa dentro de la
        transacción de escritura, y a propósito: si aquí se eligiera «la última
        otorgada» con un criterio y allí con otro, la revocación fallaría siempre
        con un motivo incomprensible. El desempate por `id` es el mismo.
        """
        with self._conexion() as cnx, cnx.cursor() as cur:
            return version_de_la_concesion_de(cur, "consentimiento_evento", sujeto_google)

    def historial(self, sujeto_google: str) -> HistorialDeConsentimiento:
        """Del más antiguo al más reciente. `id` desempata dos `momento` iguales."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                SELECT id, version, estado, comprobante, momento, categoria_edad
                  FROM consentimiento_evento
                 WHERE sujeto_google = %s
                 ORDER BY momento ASC, id ASC
                """,
                (sujeto_google,),
            )
            eventos = tuple(
                EventoConsentimiento(
                    sujeto_google=sujeto_google,
                    version=version,
                    estado=EstadoConsentimiento(estado),
                    comprobante=comprobante,
                    momento=momento,
                    secuencia=identificador,
                    categoria_edad=CategoriaDeEdad(categoria),
                )
                for identificador, version, estado, comprobante, momento, categoria
                in cur.fetchall()
            )
        return HistorialDeConsentimiento(sujeto_google=sujeto_google, eventos=eventos)

    def _vigente(
        self, cur: Any, sujeto_google: str
    ) -> tuple[EstadoConsentimiento, str | None, CategoriaDeEdad | None]:
        """El último acto —estado, versión y categoría de edad— con el mismo
        desempate que `estado_vigente_db.py`.

        La categoría es lo que permite detectar que la persona cumplió 18 desde
        que aceptó, que es la segunda puerta de renovación de `EQ-021`.
        """
        fila = ultimo_acto(
            cur,
            "consentimiento_evento",
            sujeto_google,
            ("estado", "version", "categoria_edad"),
        )
        if fila is None:
            return EstadoConsentimiento.PENDIENTE, None, None
        return EstadoConsentimiento(fila[0]), fila[1], CategoriaDeEdad(fila[2])
