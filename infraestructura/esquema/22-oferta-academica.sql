ALTER TABLE persona
    ADD COLUMN IF NOT EXISTS facultad text NOT NULL DEFAULT '';

ALTER TABLE persona
    DROP CONSTRAINT IF EXISTS persona_oferta_academica_valida;

ALTER TABLE persona
    ADD CONSTRAINT persona_oferta_academica_valida CHECK (
        facultad = '' OR
        (facultad = 'Facultad de Ingeniería' AND (programa = '' OR programa IN (
            'Tecnología en Desarrollo de Software',
            'Ingeniería Informática',
            'Ingeniería Multimedia'
        ))) OR
        (facultad = 'Facultad de Arte y Diseño' AND (programa = '' OR programa IN (
            'Tecnología en Delineante de Arquitectura e Ingeniería',
            'Arquitectura',
            'Diseño Visual'
        ))) OR
        (facultad = 'Facultad de Educación' AND (programa = '' OR programa IN (
            'Licenciatura en Español e Inglés',
            'Licenciatura en Música'
        ))) OR
        (facultad = 'Facultad de Ciencias Sociales y de la Administración' AND (programa = '' OR programa IN (
            'Tecnología en Gestión Empresarial',
            'Tecnología en Gestión Comercial y de Mercados',
            'Tecnología en Gestión Financiera',
            'Administración de Empresas',
            'Administración Financiera'
        )))
    );

ALTER TABLE rol_asignacion
    DROP CONSTRAINT IF EXISTS rol_asignacion_rol_check;

ALTER TABLE rol_asignacion
    ADD CONSTRAINT rol_asignacion_rol_check
    CHECK (rol IN ('investigador_administrador', 'docente'));
