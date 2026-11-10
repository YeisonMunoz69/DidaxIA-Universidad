from __future__ import annotations


class ErrorDeAlmacen(RuntimeError):
    pass

class AlmacenNoConfigurado(ErrorDeAlmacen):
    pass

class AlmacenNoDisponible(ErrorDeAlmacen):
    pass

class DatoNoAdmitido(ErrorDeAlmacen):
    pass

class EscrituraRechazada(ErrorDeAlmacen):
    pass

class TransicionInvalida(EscrituraRechazada):
    pass

class ReferenciaDesconocida(EscrituraRechazada):
    pass

class AlcanceIncorrecto(EscrituraRechazada):
    pass

class VersionNoVigente(EscrituraRechazada):
    pass

class PerfilSinEdad(EscrituraRechazada):
    pass
