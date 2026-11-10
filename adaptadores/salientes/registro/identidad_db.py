"""
identidad_db.py — `PuertoIdentidad` contra `persona` (migración 11)
=====================================================================

La primera relación **persistente** sujeto → perfil del sistema. Hasta hoy la
identidad de quien entraba vivía sólo en el `dict` del almacén de sesiones, en
memoria del proceso, y un reinicio la perdía entera.

Quién lo consume
------------------------
`rutas/sesion.py` al abrir sesión —`POST /api/sesion/google` registra la
identidad **antes** de crear la sesión— y `rutas/consentimiento.py` en todo el
recorrido de onboarding. `estado_vigente_db.py` reutiliza su
`perfil_desde_fila()` para no derivar el perfil de dos maneras.

⚠️ Aquí decía que «todavía no lo consume nadie» y que «cablearlo es la sesión 3».
Se cableó en el hito B1 y nadie retiró la nota, así que durante toda la Fase 3
este archivo afirmaba estar muerto mientras sostenía el inicio de sesión.

Por qué `registrar()` usa `ON CONFLICT DO UPDATE` y eso NO es sobrescribir historia
------------------------------------------------------------------------------------
`persona` es una fila por titular, no una tabla de eventos. Lo que la Fase 3
declara inmutable son las decisiones —consentimiento, asentimiento, evidencia— y
cada una tiene su propia tabla de eventos, sin ningún `ON CONFLICT`. Corregir un
nombre que Google cambió no reescribe ninguna decisión.

Lo que sí se cuida es que un ingreso no borre una declaración: el `DO UPDATE`
toca correo y nombre, y nunca edad, programa, semestre ni el límite del
representante.

⚠️ El plazo del representante empieza aquí · hito R4
--------------------------------------------------------------
`EQ-016` da **siete días para entregar** la autorización, contados desde que la
persona declara ser menor de edad. Hasta el cierre V-B el plazo lo fijaba
`rutas/consentimiento.py` **al recibir el primer PDF**, y la auditoría V-B
describió la consecuencia exacta:

    «Los siete días del menor empiezan al declarar la minoría de edad. No
    empiezan con la primera carga: sin documento el plazo actual permanece nulo y
    nunca vence.»

Es decir: quien no subía nada —justo el caso que el plazo existe para acotar—
nunca vencía, porque su `representante_limite` seguía en `NULL`. El plazo sólo
corría para quien ya había cumplido.

Ahora lo fija `declarar_perfil()`, **en el mismo `UPDATE`** que escribe la edad.
Cuatro propiedades, y las cuatro salen de esa única sentencia:

- **atómico** · edad y plazo se escriben juntos o no se escribe ninguno. No
  existe el estado «declarado menor, sin plazo» que nunca vence;
- **reloj de PostgreSQL** · `now()`, no el del proceso. Con varios procesos o un
  reloj desajustado, dos personas que declaran a la vez recibirían plazos
  distintos;
- **una sola vez** · el `CASE` conserva el valor si ya existía, así que recargar,
  volver a declarar la edad o corregir el programa no lo mueven;
- **sin fallo escondido** · si el `UPDATE` falla, falla la ruta. El
  `except: return` que lo silenciaba se retiró con `_fijar_limite()`.

`fijar_limite_representante()` se conserva para una corrección administrativa
puntual, pero **ninguna ruta la llama**: el camino normal es éste.

La clase no es una columna de aquí
--------------------------------------------
`clase_matricula` (`08-clases.sql`) ya relaciona sujeto y clase con **el mismo**
identificador estable, así que `consultar()` resuelve `clase_vinculada` con un
`EXISTS` de sólo lectura contra esa tabla. Duplicar la relación en `persona`
habría creado dos respuestas para «¿está en una clase?» y una migración que
reinterpreta filas existentes — que es justo lo que esta sesión no puede hacer.


"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import (
    RepositorioPostgres,
    exigir_persona_activa,
    exigir_sin_supresion,
)
from dominio.modelo.identidad import (
    MAYORIA_DE_EDAD,
    Identidad,
    IdentidadInvalida,
    PerfilOnboarding,
    exigir_edad_admisible,
    exigir_semestre_admisible,
)
from dominio.modelo.menores import PLAZO_REPRESENTANTE_DIAS
from dominio.puertos.almacen import ReferenciaDesconocida
from dominio.puertos.gobierno import SupresionEnCurso

if TYPE_CHECKING:  # pragma: no cover
    from datetime import datetime

#: Las columnas que forman un `PerfilOnboarding`, más la vinculación a clase
#: resuelta contra `08-clases.sql`. Una sola definición para las tres consultas.
_CAMPOS = """
    p.sujeto_google, p.correo, p.nombre, p.edad_declarada, p.facultad, p.programa, p.semestre,
    EXISTS (SELECT 1 FROM clase_matricula m WHERE m.identificador = p.sujeto_google)
"""


def perfil_desde_fila(fila: tuple) -> PerfilOnboarding:
    """La fila de `_CAMPOS` como tipo del dominio, con sus invariantes ya
    comprobadas. Compartida con `estado_vigente_db.py`, que lee lo mismo."""
    sujeto, correo, nombre, edad, facultad, programa, semestre, en_clase = fila
    return PerfilOnboarding(
        identidad=Identidad(sujeto_google=sujeto, correo=correo, nombre=nombre or ""),
        edad=edad,
        facultad=facultad or "",
        programa=programa or "",
        semestre=semestre,
        clase_vinculada=bool(en_clase),
    )


class AdaptadorIdentidadPostgres(RepositorioPostgres):
    """`PuertoIdentidad` contra `persona`. La cadena entra por el constructor."""

    def registrar(self, identidad: Identidad) -> PerfilOnboarding:
        """Deja constancia de la identidad verificada y devuelve el perfil.

        El `CASE` del nombre evita que un `id_token` sin `name` —Google no
        siempre lo manda— borre el nombre que ya se había guardado.

        ⚠️ **Con un trámite de supresión abierto NO actualiza nada** · corrección
        transversal. Entrar con Google tiene que seguir funcionando —es como se
        ejerce el derecho a consultar y a cancelar, y bloquear el login habría
        dejado a alguien sin poder cancelar su propia supresión al expirarle la
        sesión—, pero refrescar correo y nombre desde el `id_token` **es escribir
        datos nuevos** sobre quien pidió que se borren los suyos.

        Así que se recupera la fila existente y se devuelve tal cual. La persona
        entra, ve su trámite y puede cancelarlo; lo que no ocurre es que su fila
        se actualice por haber entrado.

        El caso de alguien que **no existe** y entra durante… nada: si no hay
        fila de `persona`, tampoco puede haber una `solicitud_supresion` que la
        referencie —clave foránea—, así que ese camino es el de siempre.
        """
        with self._escritura() as cnx, cnx.cursor() as cur:
            existente = self._sin_actualizar_si_hay_supresion(cur, identidad)
            if existente is not None:
                return existente
            cur.execute(
                """
                INSERT INTO persona (sujeto_google, correo, nombre)
                VALUES (%s, %s, %s)
                ON CONFLICT (sujeto_google) DO UPDATE
                SET correo = EXCLUDED.correo,
                    nombre = CASE
                                 WHEN EXCLUDED.nombre <> '' THEN EXCLUDED.nombre
                                 ELSE persona.nombre
                             END,
                    actualizada_en = now()
                """,
                (identidad.sujeto_google, identidad.correo, identidad.nombre),
            )
            return self._leer(cur, identidad.sujeto_google)

    def _sin_actualizar_si_hay_supresion(
        self, cur, identidad: Identidad
    ) -> PerfilOnboarding | None:
        """El perfil ya guardado si hay trámite abierto; `None` si no lo hay.

        Se bloquea la fila **antes** de mirar el trámite, igual que en cualquier
        otra escritura de esta frontera: sin el `FOR UPDATE`, entre comprobar y
        escribir cabría la apertura de una supresión y el `UPDATE` la pisaría.

        `exigir_persona()` levantaría `ReferenciaDesconocida` para quien todavía
        no existe, y aquí eso es el camino normal —el primer ingreso—, así que se
        consulta directamente y se distingue por el `None`.
        """
        cur.execute(
            "SELECT 1 FROM persona WHERE sujeto_google = %s FOR UPDATE",
            (identidad.sujeto_google,),
        )
        if cur.fetchone() is None:
            return None  # primer ingreso: no hay fila que preservar
        try:
            exigir_sin_supresion(cur, identidad.sujeto_google)
        except SupresionEnCurso:
            # No se levanta: entrar tiene que seguir siendo posible. Lo que se
            # evita es la escritura, no la sesión.
            return self._leer(cur, identidad.sujeto_google)
        return None

    def declarar_perfil(
        self,
        sujeto_google: str,
        *,
        edad: int | None = None,
        facultad: str = "",
        programa: str = "",
        semestre: int | None = None,
        motivo: str = "",
        origen: str = "onboarding_estudiante",
    ) -> PerfilOnboarding:
        """Guarda lo declarado en el onboarding sobre una identidad ya verificada.

        `COALESCE` y el `CASE` del programa hacen que un formulario parcial
        complete lo que trae y **no borre** lo anterior: es el mismo criterio que
        la ruta heredada ya aplica a la edad —«un cliente que todavía no pregunta
        la edad no debe poder pisar una edad ya declarada»—, extendido a los tres
        campos de `EQ-020`.
        """
        # Se valida antes de abrir conexión: un semestre imposible no merece un
        # viaje a la base, y el dominio es quien sabe qué es admisible.
        exigir_edad_admisible(edad)
        exigir_semestre_admisible(semestre)
        # Los llamados internos anteriores a la migración pueden completar un
        # perfil histórico sin facultad. El borde nuevo sí la exige; cuando
        # llega, la pareja queda validada aquí también.
        if facultad:
            from dominio.modelo.oferta_academica import (  # noqa: PLC0415
                exigir_oferta_valida,
            )

            facultad, programa = exigir_oferta_valida(facultad, programa)
        if origen not in {"onboarding_estudiante", "integracion_interna"}:
            raise IdentidadInvalida("origen de la corrección no admitido")
        with self._escritura() as cnx, cnx.cursor() as cur:
            # Cerrojo y trámite, en ese orden y dentro de esta transacción.
            # Declarar edad, programa o semestre es **aportar datos nuevos**, y
            # durante una supresión abierta eso no se registra (`EQ-022`).
            exigir_persona_activa(cur, sujeto_google)
            cur.execute(
                """
                SELECT edad_declarada, facultad, programa, semestre,
                       EXISTS (SELECT 1 FROM clase_matricula m
                                WHERE m.identificador = persona.sujeto_google)
                  FROM persona
                 WHERE sujeto_google = %s
                 FOR UPDATE
                """,
                (sujeto_google,),
            )
            anterior = cur.fetchone()
            if anterior is None:
                raise ReferenciaDesconocida("esa persona no está registrada")

            (
                edad_anterior,
                facultad_anterior,
                programa_anterior,
                semestre_anterior,
                vinculada,
            ) = anterior
            edad_nueva = edad if edad is not None else edad_anterior
            facultad_nueva = facultad or facultad_anterior or ""
            programa_nuevo = programa or programa_anterior or ""
            semestre_nuevo = semestre if semestre is not None else semestre_anterior
            cambios = {
                "edad": edad_anterior is not None and edad_nueva != edad_anterior,
                "facultad": bool(facultad_anterior) and facultad_nueva != facultad_anterior,
                "programa": bool(programa_anterior) and programa_nuevo != programa_anterior,
                "semestre": semestre_anterior is not None and semestre_nuevo != semestre_anterior,
            }
            corrige = any(cambios.values())
            motivo = str(motivo or "").strip()
            if corrige and vinculada:
                raise IdentidadInvalida(
                    "la vinculación ya fue aprobada; la corrección debe seguir la vía gobernada"
                )
            if corrige and not 8 <= len(motivo) <= 500:
                raise IdentidadInvalida(
                    "el motivo de la corrección debe tener entre 8 y 500 caracteres"
                )

            rectificacion = None
            cambia_categoria = False
            if cambios["edad"]:
                era_menor = edad_anterior < MAYORIA_DE_EDAD
                sera_menor = edad_nueva < MAYORIA_DE_EDAD
                cambia_categoria = era_menor != sera_menor
                efecto_consentimiento = (
                    "reconsentimiento_por_cambio_de_categoria"
                    if cambia_categoria else "sin_cambio_de_categoria"
                )
                efecto_asentimiento = (
                    "pasa_a_requerir" if sera_menor and not era_menor
                    else "deja_de_requerir" if era_menor and not sera_menor
                    else "sin_cambio"
                )
                if cambia_categoria:
                    cur.execute(
                        """
                        INSERT INTO rectificacion_edad_transicion
                            (rectificacion, estado, actor, motivo)
                        SELECT r.id, 'sustituida', %s,
                               'sustituida por una rectificación posterior con cambio de categoría'
                          FROM rectificacion_edad r
                         WHERE r.sujeto_google = %s
                           AND r.reconsentimiento_necesario
                           AND EXISTS (SELECT 1 FROM rectificacion_edad_transicion t
                                        WHERE t.rectificacion = r.id
                                          AND t.estado = 'reconsentimiento_pendiente')
                           AND NOT EXISTS (SELECT 1 FROM rectificacion_edad_transicion t
                                            WHERE t.rectificacion = r.id
                                              AND t.estado IN ('reconsentida', 'sustituida'))
                        ON CONFLICT (rectificacion, estado) DO NOTHING
                        """,
                        (sujeto_google, sujeto_google),
                    )
                cur.execute(
                    """
                    INSERT INTO rectificacion_edad
                        (sujeto_google, valor_anterior, valor_nuevo, actor, motivo,
                         efecto_consentimiento, efecto_asentimiento,
                         reconsentimiento_necesario, origen)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        sujeto_google, edad_anterior, edad_nueva, sujeto_google, motivo,
                        efecto_consentimiento, efecto_asentimiento, cambia_categoria, origen,
                    ),
                )
                rectificacion = int(cur.fetchone()[0])
                for estado in (
                    "registrada",
                    "reconsentimiento_pendiente" if cambia_categoria else "aplicada",
                ):
                    cur.execute(
                        "INSERT INTO rectificacion_edad_transicion "
                        "(rectificacion, estado, actor, motivo) VALUES (%s, %s, %s, %s)",
                        (
                            rectificacion,
                            estado,
                            sujeto_google,
                            motivo if estado == "registrada" else "",
                        ),
                    )
            cur.execute(
                """
                UPDATE persona
                   SET edad_declarada = COALESCE(%(edad)s, edad_declarada),
                       facultad = CASE
                                      WHEN btrim(%(facultad)s) <> '' THEN btrim(%(facultad)s)
                                      ELSE facultad
                                  END,
                       programa = CASE
                                      WHEN btrim(%(programa)s) <> '' THEN btrim(%(programa)s)
                                      ELSE programa
                                  END,
                       semestre = COALESCE(%(semestre)s, semestre),
                       -- `EQ-016` · los siete días empiezan al declarar la
                       -- minoría, en esta misma sentencia y con el reloj de la
                       -- base. El CASE lo fija SÓLO si no existía: recargar,
                       -- volver a declarar o corregir el programa no lo mueven.
                       representante_limite = CASE
                           WHEN edad_declarada IS NOT NULL
                            AND edad_declarada < %(mayoria)s
                            AND COALESCE(%(edad)s, edad_declarada) >= %(mayoria)s
                               THEN NULL
                           WHEN edad_declarada IS NOT NULL
                            AND edad_declarada >= %(mayoria)s
                            AND COALESCE(%(edad)s, edad_declarada) < %(mayoria)s
                               THEN now() + make_interval(days => %(plazo)s)
                           WHEN representante_limite IS NOT NULL THEN representante_limite
                           WHEN COALESCE(%(edad)s, edad_declarada) < %(mayoria)s
                               THEN now() + make_interval(days => %(plazo)s)
                           ELSE representante_limite
                       END,
                       actualizada_en = now()
                 WHERE sujeto_google = %(sujeto)s
                """,
                {
                    "edad": edad,
                    "facultad": facultad,
                    "programa": programa,
                    "semestre": semestre,
                    # Los dos números salen del dominio y no se escriben en el
                    # SQL: `EQ-016` fija el plazo y `EQ-020` la mayoría de edad, y
                    # una copia aquí discreparía el día que alguna cambie.
                    "mayoria": MAYORIA_DE_EDAD,
                    "plazo": PLAZO_REPRESENTANTE_DIAS,
                    "sujeto": sujeto_google,
                },
            )
            if cur.rowcount == 0:
                raise ReferenciaDesconocida("esa persona no está registrada")
            if corrige:
                if cambios["edad"]:
                    anotar(
                        cur,
                        "rectificacion_edad.aplicada",
                        actor=sujeto_google,
                        sujeto_afectado=sujeto_google,
                        detalle={
                            "rectificacion": rectificacion,
                            "cambio_categoria": cambia_categoria,
                            "reconsentimiento_necesario": cambia_categoria,
                            "origen": origen,
                            "motivo": motivo,
                            "antes": {"edad": edad_anterior},
                            "despues": {"edad": edad_nueva},
                        },
                    )
                if any(cambios[campo] for campo in ("facultad", "programa", "semestre")):
                    anotar(
                        cur,
                        "corregir_perfil_academico",
                        actor=sujeto_google,
                        sujeto_afectado=sujeto_google,
                        detalle={
                            "campos": [campo for campo in ("facultad", "programa", "semestre") if cambios[campo]],
                            "alcance": "antes_de_vinculacion",
                            "origen": origen,
                            "motivo": motivo,
                            "antes": {
                                "facultad": facultad_anterior,
                                "programa": programa_anterior,
                                "semestre": semestre_anterior,
                            },
                            "despues": {
                                "facultad": facultad_nueva,
                                "programa": programa_nuevo,
                                "semestre": semestre_nuevo,
                            },
                        },
                    )
            return self._leer(cur, sujeto_google)

    def consultar(self, sujeto_google: str) -> PerfilOnboarding | None:
        """El perfil, o `None` **sólo** si esa persona no está registrada."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                f"SELECT {_CAMPOS} FROM persona p WHERE p.sujeto_google = %s",  # noqa: S608
                (sujeto_google,),
            )
            fila = cur.fetchone()
            return perfil_desde_fila(fila) if fila else None

    def referencia_foto(self, sujeto_google: str) -> str | None:
        """La referencia opaca de la foto, nunca sus bytes ni una ruta."""
        with self._conexion() as cnx, cnx.cursor() as cur:
            cur.execute(
                "SELECT foto_perfil_referencia FROM persona WHERE sujeto_google = %s",
                (sujeto_google,),
            )
            fila = cur.fetchone()
            if fila is None:
                raise ReferenciaDesconocida("esa persona no está registrada")
            return fila[0]

    def cambiar_foto(self, sujeto_google: str, referencia: str | None) -> str | None:
        """Sustituye la referencia y devuelve la anterior dentro de una transacción."""
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, sujeto_google)
            cur.execute(
                "SELECT foto_perfil_referencia FROM persona WHERE sujeto_google = %s FOR UPDATE",
                (sujeto_google,),
            )
            anterior = cur.fetchone()[0]
            cur.execute(
                """
                UPDATE persona
                   SET foto_perfil_referencia = %s, actualizada_en = now()
                 WHERE sujeto_google = %s
                """,
                (referencia, sujeto_google),
            )
            return anterior

    def fijar_limite_representante(self, sujeto_google: str, limite: datetime) -> None:
        """Escribe la fecha límite a mano. **Ninguna ruta la llama** (hito R4).

        El camino normal es `declarar_perfil()`, que lo fija en la misma
        sentencia que la edad. Esto queda para una corrección administrativa
        puntual —una fecha mal fijada por una migración, por ejemplo— y a
        diferencia del anterior `_fijar_limite()` **propaga su fallo**: quien la
        llame se entera de que no se escribió."""
        with self._escritura() as cnx, cnx.cursor() as cur:
            cur.execute(
                """
                UPDATE persona
                   SET representante_limite = %s, actualizada_en = now()
                 WHERE sujeto_google = %s
                """,
                (limite, sujeto_google),
            )
            if cur.rowcount == 0:
                raise ReferenciaDesconocida("esa persona no está registrada")

    def _leer(self, cur: Any, sujeto_google: str) -> PerfilOnboarding:
        cur.execute(
            f"SELECT {_CAMPOS} FROM persona p WHERE p.sujeto_google = %s",  # noqa: S608
            (sujeto_google,),
        )
        return perfil_desde_fila(cur.fetchone())
