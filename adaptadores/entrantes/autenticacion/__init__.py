"""
Identidad delegada · DD-18.

El sistema NO guarda contraseñas y NO las ve nunca. La identidad la establece
el proveedor institucional por OpenID Connect.

SE PIDE EL MINIMO ALCANCE: identificador estable, correo y nombre. NO la
fotografía ni ningún otro campo. Pedir más de lo que se usa es recoger datos
sin finalidad.

SOLO EL DOMINIO INSTITUCIONAL entra, aunque se tenga el código de clase.

EL ROL NO VIENE DE AQUI. Quién es docente y quién estudiante lo determina el
servidor con sus propios registros. Si llegara del proveedor o del cliente,
bastaría cambiarlo en la petición para ver lo que no corresponde.


Contrato en OE3-Implementacion/08-Contrato-del-Turno.md

"""
