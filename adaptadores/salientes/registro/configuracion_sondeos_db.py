from __future__ import annotations

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres, exigir_persona_activa
from dominio.pedagogia.configuracion_sondeos import NODOS_CONFIGURABLES, ConfiguracionSondeos

_COLUMNAS = {
    "L-01": "l01_aula",
    "N08": "n08_digital",
    "N14": "n14_digital",
    "N05": "n05_digital",
}
_LECTURA = (
    "SELECT l01_aula, n08_digital, n14_digital, n05_digital, "
    "umbral_intentos, actualizado_en FROM configuracion_sondeos WHERE unica = true"
)


def _configuracion(fila) -> ConfiguracionSondeos:
    if fila is None:
        raise RuntimeError("falta la fila única de configuración curricular")
    return ConfiguracionSondeos(
        l01_aula=bool(fila[0]),
        n08_digital=bool(fila[1]),
        n14_digital=bool(fila[2]),
        n05_digital=bool(fila[3]),
        umbral_intentos=int(fila[4]),
        actualizado_en=fila[5].isoformat() if fila[5] else None,
    )

class AdaptadorConfiguracionSondeosPostgres(RepositorioPostgres):
    def consultar(self) -> ConfiguracionSondeos:
        with self._conexion() as cnx, cnx.cursor() as cur:
            return self.desde_cursor(cur)

    @staticmethod
    def desde_cursor(cur) -> ConfiguracionSondeos:
        cur.execute(_LECTURA)
        return _configuracion(cur.fetchone())

    def cambiar_nodo(self, nodo: str, habilitado: bool, actor: str) -> ConfiguracionSondeos:
        if nodo not in NODOS_CONFIGURABLES or not isinstance(habilitado, bool):
            raise ValueError("nodo o estado no admisible")
        columna = _COLUMNAS[nodo]
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, actor)
            cur.execute(
                f"UPDATE configuracion_sondeos SET {columna} = %s, "
                "actualizado_en = now(), actualizado_por = %s WHERE unica = true",
                (habilitado, actor),
            )
            if cur.rowcount != 1:
                raise RuntimeError("falta la fila única de configuración curricular")
            anotar(cur, "pedagogia.sondeo_configurado", actor=actor,
                   detalle={"nodo": nodo, "habilitado": habilitado})
            cur.execute(_LECTURA)
            return _configuracion(cur.fetchone())

    def cambiar_umbral(self, umbral: int, actor: str) -> ConfiguracionSondeos:
        if type(umbral) is not int or umbral not in (1, 2):
            raise ValueError("el umbral debe ser 1 o 2")
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona_activa(cur, actor)
            cur.execute(
                "UPDATE configuracion_sondeos SET umbral_intentos = %s, "
                "actualizado_en = now(), actualizado_por = %s WHERE unica = true",
                (umbral, actor),
            )
            if cur.rowcount != 1:
                raise RuntimeError("falta la fila única de configuración curricular")
            anotar(cur, "pedagogia.umbral_sondeo_configurado", actor=actor,
                   detalle={"umbral_intentos": umbral})
            cur.execute(_LECTURA)
            return _configuracion(cur.fetchone())
