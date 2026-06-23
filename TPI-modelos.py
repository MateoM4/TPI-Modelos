import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================================
# 1. BLOQUE DE VARIABLES Y PARÁMETROS GLOBALES (ESTILO MODELICA)
# =====================================================================

# --- Semilla para reproducibilidad ---
#SEMILLA_GLOBAL = 4               # Garantiza que los resultados sean los mismos en cada ejecución

# --- Parámetros de Tiempo y Llegadas ---
TIEMPO_SIMULACION = 480           # Jornada laboral en minutos (8 horas)
LLEGADA_PROMEDIO = 24             # Tiempo promedio entre llegadas de trabajos (minutos)

# --- Parámetros de Distribución Aleatoria (Tiempos de proceso) ---
TIEMPO_ESCANEO_MIN = 5            # Tiempo mínimo de escaneo por corona
TIEMPO_ESCANEO_MAX = 20           # Tiempo máximo de escaneo por corona

TIEMPO_CAD_MIN = 10               # Tiempo mínimo de diseño CAD
TIEMPO_CAD_MAX = 30               # Tiempo máximo de diseño CAD

TIEMPO_CAM_MIN = 8                # Tiempo mínimo de fresado CAM
TIEMPO_CAM_MAX = 20               # Tiempo máximo de fresado CAM

# --- Parámetros de Penalización (Colores/Discos) ---
PROBABILIDAD_PENALIZACION = 0.10  # 10% de probabilidad de tener que cambiar disco por color
TIEMPO_PENALIZACION = 5           # Minutos perdidos durante el cambio de disco

# =====================================================================
# 2. PROCESO DE LA CORONA (3 Etapas Separadas)
# =====================================================================
def proceso_corona(env, id_corona, escaneadores, disenadores, fresadoras, registros):
    tiempo_llegada = env.now
    
    ficha_trabajo = {
        'Trabajo': id_corona,
        'Minuto_Llegada': tiempo_llegada,
        'Espera_Escaneo': None,
        'Tiempo_Neto_Escaneo': None,
        'Espera_CAD': None,
        'Tiempo_Neto_CAD': None,
        'Espera_CAM': None,
        'Tiempo_Neto_CAM': None,
        'Tiempo_Total': None
    }
    registros.append(ficha_trabajo)
    
    # --- ETAPA 1: ESCANEO ---
    with escaneadores.request() as peticion_escaneo:
        yield peticion_escaneo 
        inicio_escaneo = env.now
        
        ficha_trabajo['Espera_Escaneo'] = inicio_escaneo - tiempo_llegada
        
        # Uso de los parámetros globales
        tiempo_escaneo = random.uniform(TIEMPO_ESCANEO_MIN, TIEMPO_ESCANEO_MAX)
        yield env.timeout(tiempo_escaneo)
        fin_escaneo = env.now
        ficha_trabajo['Tiempo_Neto_Escaneo'] = fin_escaneo - inicio_escaneo

    # --- ETAPA 2: DISEÑO CAD ---
    with disenadores.request() as peticion_diseno:
        yield peticion_diseno 
        inicio_diseno = env.now
        
        ficha_trabajo['Espera_CAD'] = inicio_diseno - fin_escaneo
        
        tiempo_cad = random.uniform(TIEMPO_CAD_MIN, TIEMPO_CAD_MAX)
        yield env.timeout(tiempo_cad)
        fin_diseno = env.now
        ficha_trabajo['Tiempo_Neto_CAD'] = fin_diseno - inicio_diseno

    # --- ETAPA 3: FRESADO CAM ---
    with fresadoras.request() as peticion_fresado:
        yield peticion_fresado 
        inicio_fresado = env.now
        
        ficha_trabajo['Espera_CAM'] = inicio_fresado - fin_diseno
        
        if random.random() < PROBABILIDAD_PENALIZACION: 
            yield env.timeout(TIEMPO_PENALIZACION) 
            
        tiempo_tallado = random.uniform(TIEMPO_CAM_MIN, TIEMPO_CAM_MAX)
        yield env.timeout(tiempo_tallado)
        fin_fresado = env.now
        
        ficha_trabajo['Tiempo_Neto_CAM'] = fin_fresado - inicio_fresado
        ficha_trabajo['Tiempo_Total'] = fin_fresado - tiempo_llegada

# =====================================================================
# 3. GENERADOR DE LLEGADAS
# =====================================================================
def generador_llegadas(env, escaneadores, disenadores, fresadoras, registros):
    contador = 1
    while True:
        env.process(proceso_corona(env, f'C-{contador:02d}', escaneadores, disenadores, fresadoras, registros))
        contador += 1
        yield env.timeout(random.expovariate(1.0 / LLEGADA_PROMEDIO))

# =====================================================================
# 4. MONITOR DEL SISTEMA
# =====================================================================
def monitor_sistema(env, escaneadores, disenadores, fresadoras, historial_estado):
    while True:
        historial_estado.append({
            'Minuto': env.now,
            'Cola_Escaneo': len(escaneadores.queue),
            'Cola_CAD': len(disenadores.queue),
            'Cola_CAM': len(fresadoras.queue),
            'escaneadores_Ocupados': escaneadores.count,
            'Disenadores_Ocupados': disenadores.count,
            'Fresadoras_Ocupadas': fresadoras.count
        })
        yield env.timeout(1)

# =====================================================================
# 5. MOTOR DE SIMULACIÓN Y VISUALIZACIÓN (MODIFICADO)
# =====================================================================
def ejecutar_simulacion(cant_escaneadores, cant_disenadores, cant_fresadoras, nombre_escenario, semilla_dia, verbose=True):
    # Usamos la semilla específica del día para que cada corrida sea única pero reproducible
    random.seed(semilla_dia)
    
    env = simpy.Environment()
    
    escaneadores = simpy.Resource(env, capacity=cant_escaneadores)
    disenadores = simpy.Resource(env, capacity=cant_disenadores)
    fresadoras = simpy.Resource(env, capacity=cant_fresadoras)
    
    registros = []
    historial_estado = []

    env.process(generador_llegadas(env, escaneadores, disenadores, fresadoras, registros))
    env.process(monitor_sistema(env, escaneadores, disenadores, fresadoras, historial_estado))
    
    env.run(until=TIEMPO_SIMULACION)

    df_trabajos = pd.DataFrame(registros)
    df_estado = pd.DataFrame(historial_estado)
    df_terminados = df_trabajos.dropna(subset=['Tiempo_Total'])

    # Extraemos las métricas clave del día
    trabajos_ingresados = len(df_trabajos)
    trabajos_terminados = len(df_terminados)
    espera_escaneo = df_trabajos['Espera_Escaneo'].mean(skipna=True)
    espera_cad = df_trabajos['Espera_CAD'].mean(skipna=True)
    espera_cam = df_trabajos['Espera_CAM'].mean(skipna=True)
    tiempo_total_promedio = df_terminados['Tiempo_Total'].mean() if trabajos_terminados > 0 else 0

    # Si verbose es True, imprimimos el detalle (útil para probar 1 solo día)
    if verbose:
        print(f"\n{'='*40}")
        print(f" RESULTADOS: {nombre_escenario.upper()}")
        print(f"{'='*40}")
        print(f"📦 Flujo de Trabajos:")
        print(f"  - Trabajos que ingresaron: {trabajos_ingresados}")
        print(f"  - Coronas terminadas: {trabajos_terminados}")
        print(f"  - Trabajos atascados al cierre: {trabajos_ingresados - trabajos_terminados}")
        print(f"\n⏱️  Tiempos de Espera (Cuellos de Botella):")
        print(f"  - Espera PROMEDIO para Escaneo: {espera_escaneo:.2f} min")
        print(f"  - Espera PROMEDIO para Diseño:  {espera_cad:.2f} min")
        print(f"  - Espera PROMEDIO para Máquina: {espera_cam:.2f} min")
        print(f"\n⚙️  Métricas del Sistema:")
        print(f"  - Tiempo Total Promedio por Corona: {tiempo_total_promedio:.2f} min")

    # Devolvemos un diccionario con el resumen transaccional del día
    return {
        'Dia': nombre_escenario,
        'Ingresados': trabajos_ingresados,
        'Terminados': trabajos_terminados,
        'Atascados': trabajos_ingresados - trabajos_terminados,
        'Espera_Escaneo': espera_escaneo,
        'Espera_CAD': espera_cad,
        'Espera_CAM': espera_cam,
        'Tiempo_Total_Promedio': tiempo_total_promedio
    }

# =====================================================================
# 6. SIMULACIÓN MENSUAL (30 CORRIDAS)
# =====================================================================
def simular_mes(cant_escaneadores, cant_disenadores, cant_fresadoras, nombre_escenario, semilla_base):
    print(f"\n🚀 EJECUTANDO SIMULACIÓN MENSUAL (30 DÍAS) - {nombre_escenario.upper()}...")
    
    resultados_mes = []

    # Bucle para simular 30 días independientes
    for dia in range(1, 31):
        # Generamos una semilla única para cada día basada en la semilla global
        semilla_dia = semilla_base + dia 
        
        # Ejecutamos la simulación del día en modo silencioso (verbose=False)
        metricas_dia = ejecutar_simulacion(
            cant_escaneadores, cant_disenadores, cant_fresadoras,
            nombre_escenario=f"Día {dia}",
            semilla_dia=semilla_dia,
            verbose=False
        )
        resultados_mes.append(metricas_dia)

    # Consolidamos los 30 días en un DataFrame para el análisis estadístico
    df_mes = pd.DataFrame(resultados_mes)

    # --- IMPRESIÓN DEL REPORTE MENSUAL ---
    print(f"\n{'='*50}")
    print(f" 📊 REPORTE MENSUAL CONSOLIDADO")
    print(f"{'='*50}")
    
    print(f"📦 Producción Mensual:")
    print(f"  - Total ingresados en el mes: {df_mes['Ingresados'].sum()} coronas")
    print(f"  - Total terminadas en el mes: {df_mes['Terminados'].sum()} coronas")
    print(f"  - Promedio de terminadas por día: {df_mes['Terminados'].mean():.1f} coronas/día")
    
    print(f"\n⏱️ Tiempos de Espera Promedio (Los 30 días):")
    print(f"  - Área de Escaneo: {df_mes['Espera_Escaneo'].mean():.2f} minutos")
    print(f"  - Área de Diseño:  {df_mes['Espera_CAD'].mean():.2f} minutos")
    print(f"  - Área de Fresado: {df_mes['Espera_CAM'].mean():.2f} minutos")
    
    print(f"\n⚙️ Eficiencia Global:")
    print(f"  - Tiempo de entrega promedio general: {df_mes['Tiempo_Total_Promedio'].mean():.2f} minutos")
    print(f"{'='*50}\n")

    return df_mes

# --- EJECUTAR ---
if __name__ == '__main__':
    # Definimos una lista con las semillas base que queremos probar en esta corrida
    semillas_de_prueba = [1, 50, 100, 150, 200, 250, 300, 350, 400, 450]
    
    # Guardamos los resultados de cada mes en una lista por si queremos compararlos después
    resultados_historicos = []

    for semilla in semillas_de_prueba:
        print(f"\n{'*'*60}")
        print(f" INICIANDO SIMULACIÓN CON SEMILLA BASE: {semilla}")
        print(f"{'*'*60}")
        
        # Ejecutamos el mes completo inyectando la semilla por argumento
        df_mes_actual = simular_mes(
            cant_escaneadores=2, 
            cant_disenadores=2, 
            cant_fresadoras=2, 
            nombre_escenario=f"Escenario Base (Seed {semilla})", 
            semilla_base=semilla
        )
        
        resultados_historicos.append(df_mes_actual)