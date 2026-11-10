from __future__ import annotations

from types import MappingProxyType


class OfertaAcademicaInvalida(ValueError):
    pass

FACULTAD_INGENIERIA = "Facultad de Ingeniería"
FACULTAD_ARTE = "Facultad de Arte y Diseño"
FACULTAD_EDUCACION = "Facultad de Educación"
FACULTAD_SOCIALES = "Facultad de Ciencias Sociales y de la Administración"

OFERTA_ACADEMICA = MappingProxyType(
    {
        FACULTAD_INGENIERIA: (
            "Tecnología en Desarrollo de Software",
            "Ingeniería Informática",
            "Ingeniería Multimedia",
        ),
        FACULTAD_ARTE: (
            "Tecnología en Delineante de Arquitectura e Ingeniería",
            "Arquitectura",
            "Diseño Visual",
        ),
        FACULTAD_EDUCACION: (
            "Licenciatura en Español e Inglés",
            "Licenciatura en Música",
        ),
        FACULTAD_SOCIALES: (
            "Tecnología en Gestión Empresarial",
            "Tecnología en Gestión Comercial y de Mercados",
            "Tecnología en Gestión Financiera",
            "Administración de Empresas",
            "Administración Financiera",
        ),
    }
)

FACULTADES = tuple(OFERTA_ACADEMICA)
PROGRAMAS = tuple(programa for programas in OFERTA_ACADEMICA.values() for programa in programas)


def exigir_oferta_valida(facultad: str, programa: str) -> tuple[str, str]:
    facultad = str(facultad or "").strip()
    programa = str(programa or "").strip()
    if facultad not in OFERTA_ACADEMICA:
        raise OfertaAcademicaInvalida("facultad no admitida")
    if programa not in OFERTA_ACADEMICA[facultad]:
        raise OfertaAcademicaInvalida("el programa no pertenece a la facultad seleccionada")
    return facultad, programa
