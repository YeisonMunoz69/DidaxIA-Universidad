"""Preparación gráfica con corte efectivo de tiempo y memoria.

El análisis opcional de fronteras puede exceder el plazo en expresiones
complejas. En ese caso todavía se prepara la curva, protegida por su dominio
original, y se declara que no hay evidencia de puntos especiales.
"""
import json
import subprocess
import sys

from adaptadores.salientes.simbolico.proceso_aislado import TIEMPO_MAXIMO_S


def preparar_curvas_acotadas(solicitudes):
    for estudiar in (True, False):
        try:
            proceso = subprocess.run(
                [sys.executable, '-m', __name__],
                input=json.dumps({'curvas': solicitudes, 'estudiar': estudiar}),
                text=True, encoding='utf-8', capture_output=True,
                timeout=max(1, TIEMPO_MAXIMO_S),
                check=False,
            )
        except subprocess.TimeoutExpired:
            if estudiar:
                if isinstance(solicitudes, list) and any(isinstance(c, dict) and c.get('tipo') == 'derivada' for c in solicitudes):
                    raise ValueError('no se pudo verificar el dominio de la derivada dentro del plazo; prueba con la función original o una expresión más breve') from None
                continue
            raise ValueError('la expresión superó el tiempo permitido para preparar la gráfica') from None
        if proceso.returncode:
            raise ValueError('no se pudo preparar la expresión dentro de los recursos permitidos')
        salida = json.loads(proceso.stdout)
        if 'error' in salida:
            raise ValueError(salida['error'])
        curvas = salida['curvas']
        if not estudiar:
            for curva in curvas:
                curva['dominio']['alcance'] = 'El análisis de puntos no terminó dentro del plazo; se conserva el evaluador original.'
        return curvas
    raise ValueError('no se pudo preparar la gráfica')


if __name__ == '__main__':
    from adaptadores.salientes.simbolico.graficadora import preparar_curvas
    from adaptadores.salientes.simbolico.proceso_aislado import _preparar_hijo
    _preparar_hijo()
    entrada = json.load(sys.stdin)
    try:
        salida = {'curvas': preparar_curvas(entrada['curvas'], estudiar_dominio=entrada['estudiar'])}
    except ValueError as error:
        salida = {'error': str(error)}
    print(json.dumps(salida, ensure_ascii=True, allow_nan=False))
