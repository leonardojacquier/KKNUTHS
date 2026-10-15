# Transcripción del "Catálogo de minicargadoras" (Shandong Hightop Machinery, en español), página por página.
# Chave = modelo. 'motores' quando há duas colunas de motor; valores exatamente como no catálogo.
M = {}
M['HY320T'] = dict(pag='03-04', tipo='orugas, operador de pie en plataforma (stand-on)', motores=['RATO R420', 'Briggs & Stratton 13,5 HP'],
  pot=['9,7 kW', '10 kW'], rpm=['3600', '3600'], ruido='≤95 dB', presion='0–17 MPa', caudal=['0–18 L', '0–21,6 L'],
  carga='250 kg', cucharon='0,15 m³', fuerza='360 kg', vel='0–4,5 km/h', peso='830 kg', comb='7 L', aceite='1,7 L', hidr='37 L',
  alt_trab='2120 mm', alt_pas='1865 mm', alt_desc='1405 mm', dist_desc='575 mm', ang_desc='37°', alt_total='1350 mm', suelo='121 mm',
  long_sin='1495 mm', ancho='1021 mm', ancho_cuch='1080 mm', long_con='2245 mm', long_pedal='1990 mm')
M['HYS360'] = dict(pag='05-06', tipo='orugas, operador a bordo o a pie', motor='Briggs & Stratton', pot='13,5 HP / 10,1 kW',
  carga='320 kg', cucharon='0,15 m³', vel='máx. 5 km/h', ancho='1090–1150 mm', alt_desc='1458 mm', ancho_cuch='1150 mm')
M['HY380T'] = dict(pag='07-08', tipo='orugas, operador de pie en plataforma (stand-on)', motores=['RATO R740-1', 'Briggs & Stratton 23 HP'],
  pot=['16 kW', '17 kW'], rpm=['3600', '3600'], ruido='≤95 dB', presion='0–17 MPa', caudal=['0–21,6 L', '0–21,6 L'],
  carga='300 kg', cucharon='0,15 m³', fuerza='380 kg', vel='0–4,5 km/h', peso='890 kg', comb='20 L', aceite='1,7 L', hidr='37 L',
  alt_trab='2120 mm', alt_pas='1865 mm', alt_desc='1405 mm', dist_desc='575 mm', ang_desc='37°', alt_total='1350 mm', suelo='121 mm',
  long_sin='1495 mm', ancho='1021 mm', ancho_cuch='1150 mm', long_con='2245 mm', long_pedal='1990 mm')
M['HYS380'] = dict(pag='09-10', tipo='ruedas u orugas', motores=['RATO R740-1', 'Briggs & Stratton 23 HP'],
  pot=['16 kW', '17 kW'], rpm=['3600', '3600'], ruido='≤95 dB', presion='0–17 MPa', caudal=['0–21,6 L', '0–21,6 L'],
  carga='300 kg', cucharon='0,15 m³', fuerza='380 kg', vel='0–4,5 km/h', peso='800 kg', comb='20 L', aceite='1,7 L', hidr='37 L',
  alt_trab='2120 mm', alt_pas='1890 mm', alt_desc='1465 mm', dist_desc='485 mm', ang_desc='32°', alt_total='1315 mm', suelo='115 mm',
  entre_ejes='680 mm', long_sin='1650 mm', ancho='1120 mm', ancho_cuch='1150 mm', long_con='2085 mm', long_pedal='2035 mm')
M['HYS382T'] = dict(pag='11-12', tipo='orugas', motor='Runtong', pot='19,2 kW (26 HP)', rpm='3600', ruido='≤95 dB',
  comb='28 L', hidr='20 L', presion='17 MPa (170 bar)', caudal='25 L/min (estándar)', caudal_trasl='22 / 36 L/min',
  caudal_repos='10 / 13 L/min', caudal_trabajo='44 L/min',
  carga='380 kg (62 % de la carga de vuelco)', cucharon='0,15 m³', fuerza='550 kg', vel='0–5,5 km/h', peso='860 kg',
  traccion='520 kg (sin carga)', pendiente='17°', autonomia='3–4 h (con el depósito lleno)',
  alt_trab='2200 mm', alt_pas='1884 mm', alt_desc='1488 mm', dist_desc='348 mm', giro_cuch='55°', ang_desc='30°',
  ang_salida='11°', alt_total='1280 mm', suelo='100 mm', entre_ejes='860 mm', long_sin='1780 mm', ancho='1200 mm',
  ancho_cuch='1190 mm', long_con='2500 mm', radio_giro='1307 mm', ciclo='elevación 4,27 s · carga 1,34 s · descarga 3,31 s',
  neumatico='18×8,5-8')
M['HYSL390'] = dict(pag='13-14', tipo='ruedas, operador sentado con techo', motor='Rato R420', pot='10 kW', rpm='3600', ruido='≤95 dB',
  presion='0–17 MPa', caudal='0–18 L', carga='250 kg', cucharon='0,13 m³', fuerza='200 kg', vel='0–4,5 km/h', peso='850 kg',
  comb='6,5 L', aceite='1,7 L', hidr='23 L',
  alt_trab='2398 mm', alt_pas='1815 mm', alt_desc='1430 mm', dist_desc='366 mm', ang_desc='23°', alt_total='2020 mm', suelo='185 mm',
  entre_ejes='815 mm', long_sin='2030 mm', ancho='1050 mm', ancho_cuch='1050 mm', long_con='2481 mm')
# HY-T470: el índice lo llama HYS470; la página, HY-T470. Presión "16bar" omitida (valor dudoso en el catálogo).
M['HY-T470'] = dict(pag='15-16', tipo='orugas, operador de pie en plataforma (stand-on)',
  motor='Rato / Koop / Briggs & Stratton / Yanmar / Kubota (a elección)', pot='16,8 / 15 / 17 / 17,8 / 18,5 kW (según motor)',
  cilindros='2 / 3', admision='aspiración natural', emisiones='EPA / EU5', comb='21 L',
  peso='1176 kg', cucharon='0,12 m³', pendiente='25°', arranque='5,5 kN', carga='350 kg', carga_max='480 kg', vel='0–4 km/h',
  ciclo='9 s (suma de los tres movimientos)', ancho_cuch='1070 mm', alt_carga='2024 mm', alt_desc='1376 mm', alt_trab='2561 mm',
  alt_pas='2070 mm', ang_desc='63°', alt_total='1300 mm', cola='220 mm', suelo='195 mm', dist_desc='231 mm', contacto='1300 mm',
  dims='2337 × 1070 × 1300 mm', long_con='2337 mm', long_sin='1700 mm', oruga='180 × 72 × 35')
M['HYS530'] = dict(pag='17-18', tipo='orugas, operador de pie en plataforma (stand-on)', motor='Kubota D1105 (diésel)', pot='14 kW', rpm='2200', ruido='≤93 dB',
  presion='0–17 MPa', caudal='0–32 L', carga='450 kg', cucharon='0,2 m³', fuerza='530 kg', vel='0–4,5 km/h', peso='1330 kg',
  comb='30 L', aceite='4 L', hidr='35 L',
  alt_trab='2630 mm', alt_pas='2090 mm', alt_desc='1535 mm', dist_desc='715 mm', ang_desc='38°', alt_total='1630 mm', suelo='150 mm',
  long_sin='2220 mm', ancho='1050 mm', ancho_cuch='1150 mm', long_con='2745 mm', long_pedal='2100 mm')
M['HYS530T'] = dict(pag='19-20', tipo='orugas, operador de pie en plataforma (stand-on)', motor='RATO R740', pot='17 kW', rpm='3600', ruido='≤95 dB',
  presion='0–17 MPa', caudal='0–36 L', carga='380 kg', cucharon='0,2 m³', fuerza='500 kg', vel='0–4,5 km/h',
  comb='30 L', aceite='1,5 L', hidr='35 L',
  alt_trab='2420 mm', alt_pas='2085 mm', alt_desc='1580 mm', dist_desc='755 mm', ang_desc='29°', alt_total='1630 mm', suelo='150 mm',
  long_sin='2220 mm', ancho='1070 mm', ancho_cuch='1150 mm', long_con='2725 mm', long_pedal='2055 mm')
M['HY-V1000'] = dict(pag='21-22', tipo='orugas, operador de pie en plataforma (stand-on)', motor='diésel, 3 cilindros, 1,131 L, refrigeración líquida',
  pot='18,4 kW (25 HP)', rpm='2800', ruido='≤95 dB', emisiones='EU NRMM 97/68/EC Stage 5 · EPA Tier 4 Final',
  peso='1538 kg', carga='454 kg', vuelco='1315 kg', presion_suelo='2800 kg/m²', caudal='45 L/min (auxiliar estándar)',
  vel='5,8 km/h', vel_atras='3,9 km/h', comb='25 L', hidr='22 L', bomba='45 L/min', alivio='200 bar (acoples rápidos)',
  alt_trab='3028 mm', alt_desc='1730 mm', dist_desc='900 mm', alt_total='1405 mm', long_con='2896 mm', ancho='900 mm')
M['HYS25'] = dict(pag='23-24', tipo='ruedas u orugas, cabina con operador a bordo', motor='Kubota', pot='25 HP / 2800 rpm',
  carga='380 kg', caudal='50 L/min', neumatico='6.5-10', comb='28 L', peso='1300 kg', cucharon='0,2 m³',
  alt_trab='3400 mm', alt_cabina='1813 mm', alt_desc='2000 mm', ancho_cuch='920 mm', dist_desc='441 mm', trocha='785 mm')
# HYS35: la fila de 500 kg no trae rótulo en el catálogo; es la carga operativa (coincide con el catálogo ZS ya publicado).
M['HYS35'] = dict(pag='25-26', tipo='ruedas, cabina con operador a bordo', motor='Xinchai 490 · diésel 4 cilindros en línea, refrigerado por agua, 4 tiempos',
  pot='37 kW / 2500 rpm', carga='500 kg', vuelco='1000 kg', cucharon='0,3 m³', peso='2200 kg', vel='10 km/h', caudal='60 L/min',
  comb='60 L', neumatico='8.5-15', dims='2950 × 1350 × 2000 mm',
  alt_pas='2725 mm', ancho_cuch='1400 mm', ancho='1080 mm (entre ruedas)', entre_ejes='897 mm', suelo='140 mm', ang_desc='40°',
  alt_desc='2050 mm', dist_desc='790 mm', ang_salida='20°',
  equipo='cuchara estándar · controles hidráulicos tipo joystick · acoples hidráulicos auxiliares · cabina abierta; el catálogo lista también cabina con calefacción, aire acondicionado y asistencia de arranque en frío')
M['HYS45'] = dict(pag='27-28', tipo='orugas o ruedas, cabina con operador a bordo', motor='Xinchai (China), Euro 5', pot='37 kW',
  carga='700 kg', caudal='62,5 L/min', neumatico='10-16.5', comb='70 L', peso='2700 kg', cucharon='0,4 m³',
  alt_trab='3980 mm', alt_cabina='2140 mm', alt_desc='2380 mm', ancho_cuch='1740 mm', dist_desc='700 mm', trocha='1450 mm')
M['HYS50'] = dict(pag='29-30', tipo='ruedas, cabina con operador a bordo', motor='Xinchai 490 (China)', pot='36,8 kW / 2500 rpm',
  carga='750 kg', ang_salida='23°', comb='70 L', peso='3003 kg', cucharon='0,35 m³',
  alt_trab='4058 mm', alt_cabina='2007 mm', dist_desc='675 mm', entre_ejes='999 mm', alt_desc='2303 mm', long_con='3413 mm', long_sin='2700 mm')
# HYS60 (ruedas) y HYS65 (orugas): la misma tabla en el catálogo. La fila "neumático (oruga) 300X52.5" sólo aplica a la HYS65.
_s6 = dict(motor='Xinchai (China), Euro 5', pot='36 kW', carga='700 kg', caudal='60 L/min', comb='50 L', peso='2800 kg', cucharon='0,3 m³',
  alt_trab='3350 mm', alt_cabina='2050 mm', alt_desc='2100 mm', ancho_cuch='1500 mm', dist_desc='790 mm', trocha='1102 mm')
M['HYS60'] = dict(pag='31', tipo='ruedas, cabina con operador a bordo', **_s6)
M['HYS65'] = dict(pag='32', tipo='orugas, cabina con operador a bordo', oruga='300 × 52,5', **_s6)
M['HYS75'] = dict(pag='33-34', tipo='ruedas u orugas, cabina con operador a bordo', motor='Xinchai (China), Euro 5', pot='55 kW',
  carga='1050 kg', caudal='75 L/min', neumatico='12-16.5', comb='75 L', peso='3500 kg', cucharon='0,5 m³',
  alt_trab='4070 mm', alt_cabina='2160 mm', alt_desc='2450 mm', ancho_cuch='1880 mm', dist_desc='700 mm', trocha='1500 mm')
M['HYS100'] = dict(pag='35-36', tipo='orugas, cabina con operador a bordo', pot='74,9 kW / 2400 rpm',
  peso='3600 kg', carga='1200 kg', cucharon='0,6 m³', vel='12 / 18 km/h (máx.)',
  alt_trab='4290 mm', alt_pas='3278 mm', alt_cabina='2160 mm', long_sin='2963 mm', long_con='3735 mm', alt_desc='2500 mm',
  dist_desc='700 mm', entre_ejes='1185 mm', suelo='205 mm')
M['HYS120'] = dict(pag='37-38', tipo='ruedas, cabina con operador a bordo', pot='103 kW / 2300 rpm',
  peso='4000 kg', carga='1500 kg', cucharon='0,55 m³', vel='12 / 18 km/h (máx.)',
  alt_trab='4290 mm', alt_pas='3278 mm', alt_cabina='2160 mm', long_sin='3023 mm', long_con='3795 mm', alt_desc='2500 mm',
  dist_desc='700 mm', entre_ejes='1185 mm', suelo='205 mm')
M['HYS125'] = dict(pag='39-40', tipo='orugas, cabina con operador a bordo', pot='103 kW / 2300 rpm',
  peso='5100 kg', carga='1500 kg', cucharon='0,75 m³', vel='12 / 18 km/h (máx.)',
  alt_trab='4070 mm', alt_pas='3150 mm', alt_cabina='2160 mm', long_sin='3000 mm', long_con='3795 mm', alt_desc='2450 mm',
  dist_desc='700 mm', entre_ejes='1500 mm', suelo='200 mm')
