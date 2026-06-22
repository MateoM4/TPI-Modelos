import simpy
import random
import pandas as pd
import matplotlib.pyplot as plt

# =====================================================================
# 1. BLOQUE DE VARIABLES Y PARÁMETROS GLOBALES (ESTILO MODELICA)
# =====================================================================

# --- Semilla para reproducibilidad ---
SEMILLA_GLOBAL = 42               # Garantiza que los resultados sean los mismos en cada ejecución

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
def proceso_corona(env, id_corona, escaneres, disenadores, fresadoras, registros):
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
    with escaneres.request() as peticion_escaneo:
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
def generador_llegadas(env, escaneres, disenadores, fresadoras, registros):
    contador = 1
    while True:
        env.process(proceso_corona(env, f'C-{contador:02d}', escaneres, disenadores, fresadoras, registros))
        contador += 1
        yield env.timeout(random.expovariate(1.0 / LLEGADA_PROMEDIO))

# =====================================================================
# 4. MONITOR DEL SISTEMA
# =====================================================================
def monitor_sistema(env, escaneres, disenadores, fresadoras, historial_estado):
    while True:
        historial_estado.append({
            'Minuto': env.now,
            'Cola_Escaneo': len(escaneres.queue),
            'Cola_CAD': len(disenadores.queue),
            'Cola_CAM': len(fresadoras.queue),
            'Escaneres_Ocupados': escaneres.count,
            'Disenadores_Ocupados': disenadores.count,
            'Fresadoras_Ocupadas': fresadoras.count
        })
        yield env.timeout(1)

# =====================================================================
# 5. MOTOR DE SIMULACIÓN Y VISUALIZACIÓN
# =====================================================================
def ejecutar_simulacion(cant_escaneres, cant_disenadores, cant_fresadoras, nombre_escenario):
    # Fijamos la semilla al inicio de la ejecución para repetibilidad
    random.seed(SEMILLA_GLOBAL)
    
    env = simpy.Environment()
    
    escaneres = simpy.Resource(env, capacity=cant_escaneres)
    disenadores = simpy.Resource(env, capacity=cant_disenadores)
    fresadoras = simpy.Resource(env, capacity=cant_fresadoras)
    
    registros = []
    historial_estado = []

    env.process(generador_llegadas(env, escaneres, disenadores, fresadoras, registros))
    env.process(monitor_sistema(env, escaneres, disenadores, fresadoras, historial_estado))
    
    env.run(until=TIEMPO_SIMULACION)

    df_trabajos = pd.DataFrame(registros)
    df_estado = pd.DataFrame(historial_estado)

    # --- ANÁLISIS DE DATOS ---
    print(f"\n{'='*40}")
    print(f" RESULTADOS: {nombre_escenario.upper()}")
    print(f"{'='*40}")
    
    trabajos_ingresados = len(df_trabajos)
    df_terminados = df_trabajos.dropna(subset=['Tiempo_Total'])
    trabajos_terminados = len(df_terminados)
    
    print(f"📦 Flujo de Trabajos:")
    print(f"  - Trabajos que ingresaron: {trabajos_ingresados}")
    print(f"  - Coronas terminadas: {trabajos_terminados}")
    print(f"  - Trabajos atascados al cierre: {trabajos_ingresados - trabajos_terminados}")
    
    print(f"\n⏱️  Tiempos de Espera (Cuellos de Botella):")
    print(f"  - Espera PROMEDIO para Escaneo: {df_trabajos['Espera_Escaneo'].mean(skipna=True):.2f} min")
    print(f"  - Espera PROMEDIO para Diseño:  {df_trabajos['Espera_CAD'].mean(skipna=True):.2f} min")
    print(f"  - Espera PROMEDIO para Máquina: {df_trabajos['Espera_CAM'].mean(skipna=True):.2f} min")
    
    print(f"\n⚙️  Métricas del Sistema:")
    print(f"  - Tiempo Total Promedio por Corona: {df_terminados['Tiempo_Total'].mean():.2f} min")
    
    uso_escaneres = (df_estado['Escaneres_Ocupados'].sum() / (TIEMPO_SIMULACION * cant_escaneres)) * 100
    uso_disenadores = (df_estado['Disenadores_Ocupados'].sum() / (TIEMPO_SIMULACION * cant_disenadores)) * 100
    uso_fresadoras = (df_estado['Fresadoras_Ocupadas'].sum() / (TIEMPO_SIMULACION * cant_fresadoras)) * 100
    
    print(f"  - Ocupación del área de Escaneo: {uso_escaneres:.1f}%")
    print(f"  - Ocupación del área CAD: {uso_disenadores:.1f}%")
    print(f"  - Ocupación del área CAM: {uso_fresadoras:.1f}%")

    # --- GENERACIÓN DE GRÁFICOS ---
    plt.style.use('ggplot')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    fig.canvas.manager.set_window_title(f'Simulación: {nombre_escenario}')

    ax1.plot(df_estado['Minuto'], df_estado['Cola_Escaneo'], label='Cola Escaneo (Físico)', color='purple', linewidth=2)
    ax1.plot(df_estado['Minuto'], df_estado['Cola_CAD'], label='Cola Diseño (Digital)', color='blue', linewidth=2)
    ax1.plot(df_estado['Minuto'], df_estado['Cola_CAM'], label='Cola Fresado (Máquina)', color='orange', linewidth=2)
    ax1.set_title('Dinámica de las Colas de Espera a lo largo del día', fontweight='bold')
    ax1.set_xlabel('Minutos de la jornada laboral')
    ax1.set_ylabel('Cantidad de trabajos esperando')
    ax1.legend()
    ax1.grid(True)

    ax2.bar(df_terminados['Trabajo'], df_terminados['Tiempo_Total'], color='seagreen')
    ax2.set_title('Lead Time: Tiempo total de permanencia por trabajo (Solo completados)', fontweight='bold')
    ax2.set_xlabel('Identificador del Trabajo')
    ax2.set_ylabel('Minutos')
    ax2.tick_params(axis='x', rotation=45)

    plt.tight_layout()
    plt.show()

    return df_trabajos, df_estado

# --- EJECUTAR ---
if __name__ == '__main__':
    df_base, df_estado_base = ejecutar_simulacion(cant_escaneres=1, cant_disenadores=1, cant_fresadoras=2, nombre_escenario="Escenario Base")