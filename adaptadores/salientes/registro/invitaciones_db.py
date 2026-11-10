from __future__ import annotations

from datetime import timedelta

from adaptadores.salientes.registro.auditoria_sql import anotar
from adaptadores.salientes.registro.autorizacion_sql import exigir_investigador_administrador
from adaptadores.salientes.registro.base_postgres import RepositorioPostgres, exigir_persona
from dominio.modelo.invitaciones import EstadoDeInvitacion, InvitacionDeRol
from dominio.modelo.roles import Rol
from dominio.puertos.almacen import EscrituraRechazada


def _correo(valor: str) -> str:
    normalizado = str(valor or "").strip().lower()
    if normalizado.count("@") != 1 or not normalizado.endswith("@unimayor.edu.co"):
        raise ValueError("la invitación exige un correo unimayor.edu.co")
    local = normalizado.split("@", 1)[0]
    if not local or any(caracter.isspace() for caracter in normalizado):
        raise ValueError("el correo institucional no es válido")
    return normalizado

def _fila(fila) -> InvitacionDeRol:
    return InvitacionDeRol(
        secuencia=fila[0], correo=fila[1], rol=Rol(fila[2]), emitida_por=fila[3],
        emitida_en=fila[4], expira_en=fila[5], estado=EstadoDeInvitacion(fila[6]),
        aceptada_en=fila[7], revocada_en=fila[8],
    )

_COLUMNAS = (
    "id, correo, rol, emitida_por, emitida_en, expira_en, estado, "
    "aceptada_en, revocada_en"
)


class AdaptadorInvitacionesPostgres(RepositorioPostgres):
    def __init__(self, cadena_de_conexion: str, propietarios: frozenset[str] = frozenset()):
        super().__init__(cadena_de_conexion)
        self._propietarios = frozenset(correo.lower() for correo in propietarios)

    def _autorizar(self, cur, actor: str, rol: Rol) -> None:
        exigir_investigador_administrador(cur, actor)
        if rol is not Rol.INVESTIGADOR_ADMINISTRADOR:
            return
        cur.execute("SELECT lower(correo) FROM persona WHERE sujeto_google = %s", (actor,))
        fila = cur.fetchone()
        if fila is None or fila[0] not in self._propietarios:
            raise EscrituraRechazada("sólo una cuenta propietaria administra investigadores")

    def emitir(
        self, correo: str, rol: Rol, *, emisor: str, token_huella: str,
        vigencia: timedelta,
    ) -> InvitacionDeRol:
        correo = _correo(correo)
        rol = Rol(rol)
        if vigencia <= timedelta() or vigencia > timedelta(days=30):
            raise ValueError("la vigencia debe estar entre un instante y 30 días")
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, emisor)
            self._autorizar(cur, emisor, rol)
            cur.execute(
                "UPDATE invitacion_rol SET estado = 'expirada' "
                "WHERE estado = 'pendiente' AND expira_en <= now()"
            )
            cur.execute(
                f"INSERT INTO invitacion_rol "
                "(correo, rol, token_huella, emitida_por, expira_en) "
                "VALUES (%s, %s, %s, %s, now() + %s) "
                f"RETURNING {_COLUMNAS}",
                (correo, rol.value, token_huella, emisor, vigencia),
            )
            invitacion = _fila(cur.fetchone())
            anotar(
                cur, "invitacion.emitida", actor=emisor,
                detalle={"invitacion": invitacion.secuencia, "rol": rol.value},
            )
        return invitacion

    def listar(self, actor: str) -> tuple[InvitacionDeRol, ...]:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_investigador_administrador(cur, actor)
            cur.execute(
                "UPDATE invitacion_rol SET estado = 'expirada' "
                "WHERE estado = 'pendiente' AND expira_en <= now()"
            )
            anotar(cur, "invitacion.consultada", actor=actor, detalle={"limite": 100})
            cur.execute(
                f"SELECT {_COLUMNAS} FROM invitacion_rol "
                "ORDER BY emitida_en DESC, id DESC LIMIT 100"
            )
            return tuple(_fila(fila) for fila in cur.fetchall())

    def revocar(self, secuencia: int, *, actor: str) -> InvitacionDeRol | None:
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, actor)
            cur.execute(
                "SELECT rol FROM invitacion_rol WHERE id = %s FOR UPDATE", (secuencia,)
            )
            fila = cur.fetchone()
            if fila is None:
                return None
            rol = Rol(fila[0])
            self._autorizar(cur, actor, rol)
            cur.execute(
                "UPDATE invitacion_rol SET estado = 'revocada', "
                "revocada_por = %s, revocada_en = now() "
                "WHERE id = %s AND estado = 'pendiente' AND expira_en > now() "
                f"RETURNING {_COLUMNAS}",
                (actor, secuencia),
            )
            fila = cur.fetchone()
            if fila is None:
                raise EscrituraRechazada("sólo se revoca una invitación pendiente y vigente")
            invitacion = _fila(fila)
            anotar(
                cur, "invitacion.revocada", actor=actor,
                detalle={"invitacion": secuencia, "rol": rol.value},
            )
            return invitacion

    def aceptar_del_primer_inicio(
        self, correo: str, sujeto: str, token_huella: str
    ) -> tuple[Rol, ...]:
        correo = _correo(correo)
        aceptados: list[Rol] = []
        with self._escritura() as cnx, cnx.cursor() as cur:
            exigir_persona(cur, sujeto)
            cur.execute(
                "UPDATE invitacion_rol SET estado = 'expirada' "
                "WHERE estado = 'pendiente' AND expira_en <= now()"
            )
            cur.execute(
                "SELECT id, rol, emitida_por FROM invitacion_rol "
                "WHERE lower(correo) = %s AND token_huella = %s "
                "AND estado = 'pendiente' AND expira_en > now() "
                "ORDER BY emitida_en, id FOR UPDATE",
                (correo, token_huella),
            )
            for secuencia, valor_rol, emisor in cur.fetchall():
                rol = Rol(valor_rol)
                cur.execute(
                    "INSERT INTO rol_asignacion (sujeto_google, rol, otorgado_por) "
                    "SELECT %s, %s, emitida_por FROM invitacion_rol WHERE id = %s "
                    "ON CONFLICT (sujeto_google, rol) WHERE revocado_en IS NULL DO NOTHING",
                    (sujeto, rol.value, secuencia),
                )
                cur.execute(
                    "UPDATE invitacion_rol SET estado = 'aceptada', aceptada_por = %s, "
                    "aceptada_en = now() WHERE id = %s",
                    (sujeto, secuencia),
                )
                anotar(
                    cur, "invitacion.aceptada", actor=sujeto, sujeto_afectado=sujeto,
                    detalle={"invitacion": secuencia, "rol": rol.value},
                )
                anotar(
                    cur, "rol.asignado", actor=emisor, sujeto_afectado=sujeto,
                    detalle={"rol": rol.value, "origen": "invitacion"},
                )
                aceptados.append(rol)
        return tuple(aceptados)
