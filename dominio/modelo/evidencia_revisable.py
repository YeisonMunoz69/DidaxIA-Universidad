"""
evidencia_revisable.py — Lo que un investigador puede leer de una evidencia (C2A)
==================================================================================

`IntentoDeEvidencia` es el tipo del **almacén**: lo que se persiste cuando una
carga entra, y lleva la `referencia` opaca al archivo privado porque sin ella no
habría forma de recuperarlo. Este módulo es el tipo del **borde**: lo que sale
hacia quien revisa.

Son dos tipos y no uno, y la diferencia es exactamente un campo
------------------------------------------------------------------------
`EvidenciaRevisable` **no tiene `referencia`**, y ésa es toda la garantía de que
no se filtra. No es una convención («acuérdate de no serializarla»), no es un
filtro en la ruta que alguien pueda olvidar al añadir la cuarta consulta, y no es
una prueba que compruebe la salida de hoy: es que el dato **no existe en el
tipo**. Para exponerlo habría que añadirle un campo, que es un cambio visible en
una revisión, y no basta con descuidar un `dict`.

Reutilizar `IntentoDeEvidencia` en la cola habría sido más corto y habría puesto
la referencia a un `getattr` de distancia de cada respuesta JSON. `EQ-021` pide
que el archivo viva en custodia privada; una referencia publicada en una lista
paginada es la primera mitad de perderla.

El motivo viaja en el detalle y no en la cola
---------------------------------------------------
`EQ-021` exige un motivo comprensible al rechazar, y una decisión histórica sin
él deja de ser comprensible en cuanto pasan dos semanas: el detalle lo conserva.
La **cola** no lo lleva, y no por tamaño — es texto libre escrito por una persona
sobre otra, y arrastrarlo por cada fila de cada página multiplicaría su
circulación sin que nada lo consumiera.

La separación no depende de que el serializador se acuerde: la consulta de la
cola **no selecciona esa columna** (`_SQL_PROYECCION` en `menores_db.py`), así
que una página no puede traerlo ni por descuido.

Qué NO lleva, y por qué se dice en negativo
---------------------------------------------------
Ni nombre, ni correo, ni teléfono, ni un solo dato del representante legal. Ni
`revisada_por`: quién resolvió una evidencia está en `representante_revision` y
es auditable, pero publicarlo en la consola convertiría cada decisión en un
señalamiento entre colegas sin que nadie lo haya decidido. La
tabla tampoco los tiene (`11-identidad-consentimiento.sql` lo comenta), así que
aquí no hay nada que filtrar — pero el encargo de C2A pide decirlo explícitamente
porque el panel C2B va a querer «mostrar de quién es esto», y la respuesta tiene
que ser el **sujeto estable** que ya existe, no una identidad nueva compuesta
para la pantalla. Añadir cualquiera de esos campos es una decisión del equipo y
no de quien escriba la siguiente consulta.

El estado se deriva de la última revisión, no se guarda
------------------------------------------------------------------
Mismo criterio que `estado_representante()`: `representante_revision` es la
verdad y una columna `estado` sería una segunda que puede quedarse vieja. Aquí
`EstadoDeEvidencia` sale de si hay revisión y de qué dijo.

⚠️ **`EstadoDeEvidencia` no es `EstadoRepresentante`.** Se parecen y responden a
preguntas distintas: `EstadoRepresentante` es la **dimensión de una persona**
—seis valores, uno de ellos `vencido`, derivado de la versión requerida y del
plazo— y `EstadoDeEvidencia` es **un intento concreto**: o está sin revisar, o se
aprobó, o se rechazó. Fundirlos habría hecho que filtrar la cola por «pendiente»
significara dos cosas a la vez.

El cursor, y por qué es opaco pero no está firmado
-----------------------------------------------------------
`PosicionDeCursor` codifica el par `(recibido_en, id)` —la clave de orden real—
en base64url. Es **opaco**: el cliente no puede componerlo a mano ni deducir un
esquema de paginación del que después dependa, y si lo manipula recibe un rechazo
con motivo en vez de una página arbitraria.

**No está firmado, y es deliberado.** Firmarlo exigiría un secreto, y un secreto
exigiría leer una variable de entorno **dentro del dominio**, que es precisamente
lo que este árbol no hace. Y no haría falta: un cursor no concede nada. Cada
petición vuelve a comprobar el rol vigente contra PostgreSQL, así que lo único
que un cursor manipulado puede lograr es empezar la lista en otro sitio **de la
misma lista que su portador ya tenía derecho a ver**. Un cursor firmado
protegería de un ataque que no existe a cambio de una dependencia que sí.

Offset descartado
-----------------------
`LIMIT n OFFSET m` sobre una cola que recibe cargas mientras se pagina salta
filas y repite otras: si entra una evidencia nueva entre la página 1 y la 2, todo
se desplaza. Con la clave de orden en el cursor, una fila nueva no mueve a las
que ya se leyeron. El desempate por `id` es lo que hace que dos evidencias con el
**mismo** `recibido_en` —que ocurre de verdad: `now()` es el instante de la
transacción, así que dos filas de la misma transacción lo comparten— tengan un
orden total y no se pisen.


"""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from dominio.modelo.menores import TIPO_MIME_ESPERADO, ResultadoDeRevision

#: Cuántas evidencias puede pedir una página. El mínimo es 1 —pedir cero es un
#: error de quien llama, no una página vacía— y el máximo acota lo que una sola
#: petición puede arrastrar. Cien es el techo que fija el encargo de C2A.
LIMITE_MINIMO = 1
LIMITE_MAXIMO = 100
LIMITE_POR_DEFECTO = 20


class ConsultaInvalida(ValueError):
    """Un parámetro de consulta que no se puede aceptar.

    `ValueError` y no un `ErrorDeAlmacen`: no es que el almacén se niegue, es que
    la petición está mal formada y se corrige cambiándola. El borde lo traduce a
    400 y el motivo nunca interpola el valor recibido — un cursor manipulado
    podría llevar cualquier cosa dentro, y devolverlo lo convertiría en un
    reflejo del que alguien pueda tirar.
    """


class EstadoDeEvidencia(StrEnum):
    """Cómo está **un intento**. Ver el aviso de la cabecera: no es
    `EstadoRepresentante`, que describe la dimensión de una persona."""

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"


class FiltroDeEvidencias(StrEnum):
    """Lo que la cola admite filtrar. `TODOS` es un valor y no la ausencia de
    filtro: pedir todo es una decisión, y escribirla evita que un parámetro
    ausente y uno vacío signifiquen cosas distintas por accidente."""

    PENDIENTE = "pendiente"
    APROBADA = "aprobada"
    RECHAZADA = "rechazada"
    TODOS = "todos"


#: Sin decir nada, la cola es la de trabajo pendiente. Es el uso que C2B tendrá
#: el 99 % del tiempo, y hacerlo explícito en el cliente sólo añadiría una forma
#: de equivocarse.
FILTRO_POR_DEFECTO = FiltroDeEvidencias.PENDIENTE


def filtro_desde(valor: object) -> FiltroDeEvidencias:
    """El filtro pedido, o el de por defecto. Levanta si no es ninguno.

    **Ausente y vacío son lo mismo aquí**, y a propósito: un formulario que
    envíe `?estado=` porque su selector está en blanco quiere decir «no elijo»,
    no «elijo la cadena vacía». Un valor *presente y desconocido* sí levanta:
    devolver silenciosamente la cola pendiente a quien pidió `?estado=aprovada`
    le enseñaría una lista y le haría creer que está aprobada.
    """
    if valor is None:
        return FILTRO_POR_DEFECTO
    texto = str(valor).strip().lower()
    if not texto:
        return FILTRO_POR_DEFECTO
    try:
        return FiltroDeEvidencias(texto)
    except ValueError:
        admitidos = ", ".join(f.value for f in FiltroDeEvidencias)
        raise ConsultaInvalida(f"estado no admitido; los admitidos son: {admitidos}") from None


def limite_desde(valor: object) -> int:
    """El tamaño de página pedido, validado. Ausente o vacío es el de por defecto.

    Se rechaza lo que está fuera de rango en vez de recortarlo. Recortar un 500 a
    100 devolvería una página que no es la pedida sin decirlo, y quien paginara
    contando elementos se desincronizaría sin ninguna señal; un 400 se corrige.

    `True` es `int` en Python y aquí no vale: `?limite=true` no es una cantidad.
    """
    if valor is None:
        return LIMITE_POR_DEFECTO
    if isinstance(valor, bool):
        raise ConsultaInvalida("límite tiene que ser un número entero")
    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return LIMITE_POR_DEFECTO
        if not texto.isdigit():
            raise ConsultaInvalida("límite tiene que ser un número entero")
        valor = int(texto)
    if not isinstance(valor, int):
        raise ConsultaInvalida("límite tiene que ser un número entero")
    if not LIMITE_MINIMO <= valor <= LIMITE_MAXIMO:
        raise ConsultaInvalida(
            f"límite tiene que estar entre {LIMITE_MINIMO} y {LIMITE_MAXIMO}"
        )
    return valor


@dataclass(frozen=True, slots=True)
class PosicionDeCursor:
    """Dónde se quedó la página anterior: la clave de orden real, no un número.

    Los dos campos son exactamente los del `ORDER BY`. Si algún día el orden
    cambiara, este tipo tendría que cambiar con él —y eso es una ventaja: un
    cursor que no refleje la clave de orden es la forma de producir saltos y
    repeticiones sin que nadie lo note.
    """

    recibido_en: datetime
    evidencia: int

    def __post_init__(self) -> None:
        if not isinstance(self.recibido_en, datetime):
            raise ConsultaInvalida("la posición del cursor lleva una fecha")
        if self.recibido_en.tzinfo is None:
            # Una fecha sin zona compara de forma ambigua contra un
            # `timestamptz`, y el desenlace dependería del huso del servidor.
            raise ConsultaInvalida("la posición del cursor lleva una fecha con zona")
        if isinstance(self.evidencia, bool) or not isinstance(self.evidencia, int):
            raise ConsultaInvalida("la posición del cursor lleva un identificador")
        if self.evidencia < 1:
            raise ConsultaInvalida("la posición del cursor lleva un identificador")

    def codificar(self) -> str:
        """El cursor opaco y **estable**: la misma fila da siempre el mismo texto.

        Sin relleno `=` porque un cursor viaja en una cadena de consulta y el
        relleno obliga a escaparlo; `descodificar()` lo repone.
        """
        crudo = f"{self.recibido_en.isoformat()}|{self.evidencia}".encode()
        return base64.urlsafe_b64encode(crudo).decode("ascii").rstrip("=")

    @classmethod
    def descodificar(cls, texto: str) -> PosicionDeCursor:
        """El cursor de vuelta, o `ConsultaInvalida`.

        Estricto en todo: base64url válido, UTF-8 válido, exactamente dos partes,
        fecha ISO con zona e identificador entero positivo. Lo que no cumple
        **todo** se rechaza con 400 en vez de degradarse a «desde el principio»:
        empezar la lista en otro sitio del que el cliente cree es exactamente
        cómo se salta una evidencia sin que nadie se entere.
        """
        if not isinstance(texto, str) or not texto.strip():
            raise ConsultaInvalida("cursor no válido")
        crudo = texto.strip()
        relleno = "=" * (-len(crudo) % 4)
        try:
            plano = base64.urlsafe_b64decode(crudo + relleno).decode("utf-8")
        except (binascii.Error, ValueError, UnicodeDecodeError):
            raise ConsultaInvalida("cursor no válido") from None
        fecha, separador, identificador = plano.partition("|")
        if not separador or not identificador.isdigit():
            raise ConsultaInvalida("cursor no válido") from None
        try:
            momento = datetime.fromisoformat(fecha)
        except ValueError:
            raise ConsultaInvalida("cursor no válido") from None
        try:
            return cls(recibido_en=momento, evidencia=int(identificador))
        except ConsultaInvalida:
            # `__post_init__` ya rechazó fecha sin zona o identificador cero. Se
            # reescribe con el motivo genérico: quien manipula un cursor no
            # merece un diagnóstico de qué parte falló.
            raise ConsultaInvalida("cursor no válido") from None


def cursor_desde(valor: object) -> PosicionDeCursor | None:
    """El cursor pedido, o `None` para la primera página."""
    if valor is None:
        return None
    texto = str(valor).strip()
    if not texto:
        return None
    return PosicionDeCursor.descodificar(texto)


@dataclass(frozen=True, slots=True)
class EvidenciaRevisable:
    """Una evidencia vista por quien la revisa. **Sin la referencia al archivo.**

    Conserva la proyección técnica de C2A y la identidad académica decidida para
    la revisión: nombre del estudiante y nombres de sus clases. `sujeto_google`
    sigue siendo la referencia estable para agrupar intentos; nunca se añaden
    correo ni datos personales del representante legal.
    """

    evidencia: int
    sujeto_google: str
    intento: int
    version: str
    sha256: str
    tamano_bytes: int
    recibido_en: datetime
    tipo_mime: str = TIPO_MIME_ESPERADO
    #: Los dos van juntos o no van, como en `AsignacionDeRol.revocado_*`: una
    #: revisión sin fecha no se puede situar en el tiempo y una fecha sin
    #: resultado no dice qué se decidió.
    resultado: ResultadoDeRevision | None = None
    revisada_en: datetime | None = None
    #: El motivo de la última revisión · sólo el **detalle** lo transporta.
    #:
    #: `EQ-021` lo exige al rechazar —«motivo comprensible de rechazo»— y la
    #: base lo obliga con un CHECK. Aquí es texto libre escrito por una persona
    #: sobre otra, así que se transporta donde hace falta y en ningún otro sitio:
    #: la cola del revisor pinta una lista y no lo necesita, y una consulta que
    #: lo arrastrara por cada fila multiplicaría su circulación sin motivo.
    #:
    #: La separación no vive sólo aquí: la consulta de la cola **no selecciona
    #: esa columna**, así que una página no puede traerlo ni por descuido.
    #: Vacío cuando no hay revisión, y eso sí se comprueba.
    motivo: str = ""
    #: Identidad académica que necesita quien revisa para saber de quién y de
    #: qué curso proviene el documento. Nunca incluye correo ni datos del
    #: representante legal.
    estudiante_nombre: str = ""
    clases: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self._exigir_textos()
        self._exigir_cuentas()
        if not isinstance(self.recibido_en, datetime):
            raise ConsultaInvalida("una evidencia conserva cuándo se recibió")
        self._exigir_revision_completa()

    def _exigir_textos(self) -> None:
        """Los tres campos de texto, sin espacios de sobra y no vacíos."""
        for campo in ("sujeto_google", "version", "sha256"):
            valor = getattr(self, campo)
            if not isinstance(valor, str) or not valor.strip():
                raise ConsultaInvalida(f"{campo} no puede quedar vacío")
            object.__setattr__(self, campo, valor.strip())

    def _exigir_cuentas(self) -> None:
        """Los tres enteros positivos. `True` es `int` y ninguno de los tres."""
        for campo, motivo in (
            ("evidencia", "el identificador de la evidencia es un entero positivo"),
            ("intento", "el número de intento empieza en 1"),
            ("tamano_bytes", "el tamaño es un número de bytes"),
        ):
            valor = getattr(self, campo)
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
                raise ConsultaInvalida(motivo)

    def _exigir_revision_completa(self) -> None:
        """Resultado y fecha van juntos, o no van.

        Regla con nombre propio, como `AsignacionDeRol._exigir_revocacion_auditada()`:
        una revisión sin fecha no se puede situar en el tiempo y una fecha sin
        resultado no dice qué se decidió. Las dos mitades sueltas producirían un
        `estado` que la pantalla pintaría mal en direcciones opuestas.
        """
        if self.resultado is not None:
            object.__setattr__(self, "resultado", ResultadoDeRevision(self.resultado))
        if (self.resultado is None) != (self.revisada_en is None):
            raise ConsultaInvalida("una revisión lleva resultado y fecha, o no se registra")
        if self.revisada_en is not None and not isinstance(self.revisada_en, datetime):
            raise ConsultaInvalida("revisada_en tiene que ser una fecha")
        motivo = (self.motivo or "").strip()
        if motivo and self.resultado is None:
            # Un motivo sin revisión no puede significar nada: no hay decisión a
            # la que explique. Se rechaza en vez de ignorarse, porque una fila
            # así indicaría que la consulta juntó columnas de dos sitios.
            raise ConsultaInvalida("un motivo sin revisión no explica ninguna decisión")
        object.__setattr__(self, "motivo", motivo)
        object.__setattr__(self, "estudiante_nombre", (self.estudiante_nombre or "").strip())
        object.__setattr__(
            self,
            "clases",
            tuple(nombre.strip() for nombre in self.clases if isinstance(nombre, str) and nombre.strip()),
        )

    @property
    def estado(self) -> EstadoDeEvidencia:
        """Sin revisión es `PENDIENTE`; con ella, lo que dijo."""
        if self.resultado is None:
            return EstadoDeEvidencia.PENDIENTE
        if self.resultado is ResultadoDeRevision.APROBADA:
            return EstadoDeEvidencia.APROBADA
        return EstadoDeEvidencia.RECHAZADA

    @property
    def posicion(self) -> PosicionDeCursor:
        """Su lugar en el orden de la cola. Lo usa la página para decir dónde
        continuar sin que quien pagina tenga que componerlo."""
        return PosicionDeCursor(recibido_en=self.recibido_en, evidencia=self.evidencia)


@dataclass(frozen=True, slots=True)
class PaginaDeEvidencias:
    """Un tramo de la cola, y por dónde sigue.

    `cursor_siguiente` es `None` **exactamente cuando no hay más**, y por eso no
    hace falta un `hay_mas` que pudiera contradecirlo: la propiedad lo deriva. Un
    cliente que pagine «hasta que el cursor sea nulo» nunca pide una página de
    más ni se detiene una de menos.

    Una página vacía es una respuesta legítima —la cola pendiente vacía es el
    estado sano del sistema— y no un error ni un 404.
    """

    evidencias: tuple[EvidenciaRevisable, ...] = ()
    cursor_siguiente: str | None = None

    @property
    def hay_mas(self) -> bool:
        return self.cursor_siguiente is not None
