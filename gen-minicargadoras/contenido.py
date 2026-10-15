# Copy en español de la línea de minicargadoras. Los números vienen de dados.py (catálogo del fabricante).
MARCA = 'HIGHTOP'
# modelo: (configuración corta, carga operativa, potencia corta, familia)
#   familia: 'pie' = compacta con operador de pie o caminando · 'techo' = sentado con techo · 'cabina' = skid steer con cabina
CURTO = {
 'HY320T':   ('Orugas · operador de pie', '250 kg', '9,7–10 kW', 'pie'),
 'HYS360':   ('Orugas · a bordo o a pie', '320 kg', '10,1 kW (13,5 HP)', 'pie'),
 'HY380T':   ('Orugas · operador de pie', '300 kg', '16–17 kW', 'pie'),
 'HYS380':   ('Ruedas u orugas', '300 kg', '16–17 kW', 'pie'),
 'HYS382T':  ('Orugas', '380 kg', '19,2 kW (26 HP)', 'pie'),
 'HYSL390':  ('Ruedas · sentado con techo', '250 kg', '10 kW', 'techo'),
 'HY-T470':  ('Orugas · operador de pie', '350 kg', '15–18,5 kW', 'pie'),
 'HYS530':   ('Orugas · operador de pie', '450 kg', '14 kW diésel', 'pie'),
 'HYS530T':  ('Orugas · operador de pie', '380 kg', '17 kW', 'pie'),
 'HY-V1000': ('Orugas · operador de pie', '454 kg', '18,4 kW diésel', 'pie'),
 'HYS25':    ('Ruedas u orugas · cabina', '380 kg', '25 HP', 'cabina'),
 'HYS35':    ('Ruedas · cabina', '500 kg', '37 kW diésel', 'cabina'),
 'HYS45':    ('Orugas o ruedas · cabina', '700 kg', '37 kW', 'cabina'),
 'HYS50':    ('Ruedas · cabina', '750 kg', '36,8 kW', 'cabina'),
 'HYS60':    ('Ruedas · cabina', '700 kg', '36 kW', 'cabina'),
 'HYS65':    ('Orugas · cabina', '700 kg', '36 kW', 'cabina'),
 'HYS75':    ('Ruedas u orugas · cabina', '1.050 kg', '55 kW', 'cabina'),
 'HYS100':   ('Orugas · cabina', '1.200 kg', '74,9 kW', 'cabina'),
 'HYS120':   ('Ruedas · cabina', '1.500 kg', '103 kW', 'cabina'),
 'HYS125':   ('Orugas · cabina', '1.500 kg', '103 kW', 'cabina'),
}
FAMILIA = {
 'pie': ('Minicargadora compacta',
   'Entra por portones, pasillos y patios donde no pasa una minicargadora con cabina, y reemplaza el trabajo a pala y carretilla: '
   'carga y traslado de material, zanjas, hoyos, nivelación y paisajismo.'),
 'techo': ('Minicargadora con asiento y techo',
   'Sobre ruedas, con asiento y techo para el operador: pensada para jornadas largas de carga y traslado de material en obras, '
   'viveros, galpones y predios, con el tamaño de una minicargadora compacta.'),
 'cabina': ('Minicargadora con cabina (skid steer)',
   'La minicargadora clásica de obra, con cabina y operador a bordo: carga de camiones, movimiento de tierra y áridos, limpieza '
   'de obra y trabajo con implementos hidráulicos —balde, horquilla, martillo, hoyadora, zanjadora, barredora y más—.'),
}
# frase extra según cómo se opera, sólo cuando el catálogo lo muestra
OPERADOR = {'de pie': 'El operador trabaja de pie en la plataforma trasera, con visión directa sobre el implemento.',
            'a bordo o a pie': 'Se opera a bordo o caminando detrás de la máquina, según el trabajo.'}
LINHA_NOME = 'Línea de Minicargadoras'
LINHA_NOTE = ('Línea completa de minicargadoras: 20 modelos, desde compactas de 250 kg con operador de pie hasta skid steer '
              'con cabina de 1.500 kg, sobre ruedas u orugas, y más de 80 implementos.')
IMPL_NOME = 'Implementos para Minicargadora'
IMPL_NOTE = ('Más de 80 implementos para minicargadora: baldes, horquillas, martillo hidráulico, hoyadora, zanjadora, '
             'barredoras, fresadora, desbrozadoras y más.')
