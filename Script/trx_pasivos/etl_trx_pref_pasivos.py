import urllib
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from datetime import date
 
# ============================================================================
# CONFIGURACIÓN Y CONEXIONES
# ============================================================================
 
def crear_engine(server, database):
    """Crea un engine de SQL Server con autenticación Windows"""
    params = urllib.parse.quote_plus(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        "Trusted_Connection=yes;"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    return create_engine(
        f"mssql+pyodbc:///?odbc_connect={params}",
        fast_executemany=True,
        pool_pre_ping=True,
    )
 
 
# Conexión a BFP_DATAWAREHOUSE
engine_origen = crear_engine("SBIBFPR03", "BFP_DATAWAREHOUSE")
 
# Conexión a BFPMARKETING
engine_destino = crear_engine("SBDBFPR15", "BFPMARKETING")
 
 
# ============================================================================
# QUERY PRINCIPAL
# ============================================================================
 
SQL_RUM = r"""
SET NOCOUNT ON;
 
declare  @dia_inicial date, @ctiempo_inicial int;
set @dia_inicial = GETDATE() -1;
--set @dia_inicial='2026-06-27'
set @ctiempo_inicial = (select ctiempo from BFP_DATAWAREHOUSE..Tiempo where Fecha = @dia_inicial); 

select cast(NumeroOperacion as int) as NumeroOperacion,cProducto,cast(CodigoClienteBanco as int) as CodigoClienteBanco,FechaValor,Narrativa,Importe,
case when cMoneda =129 then 'PEN' when cMoneda=170 then 'USD' end moneda,case
 
	when lote = 26 then 'APP'
 
	when lote in (32,33) then 'HBK'
 
	when lote = 8700 then 'PAGO SERVICIOS'
 
	when lote in (8540,8541) then 'COMPRAS'
 
	when lote = 9360 then 'PAGO INTERESES CUENTA'
 
	when lote = 4903 then 'ATM' --ATM
 
	when lote IN (3, 7) then 'INTERBANCARIO ENTRADA'
 
	WHEN lote BETWEEN 2101 AND 2120 THEN 'OF. PRINCIPAL'
    WHEN lote BETWEEN 2121 AND 2140 THEN 'AG. CAPON'
    WHEN lote BETWEEN 2141 AND 2160 THEN 'AG. CORPAC'
    WHEN lote BETWEEN 2161 AND 2180 THEN 'AG. CALLAO'
    WHEN lote BETWEEN 2181 AND 2200 THEN 'AG. COLONIAL'
    WHEN lote BETWEEN 2201 AND 2220 THEN 'AG. EMANCIPACION'
    WHEN lote BETWEEN 2221 AND 2240 THEN 'AG. SAN FELIPE'
    WHEN lote BETWEEN 2241 AND 2260 THEN 'AG. RISSO'
    WHEN lote BETWEEN 2261 AND 2280 THEN 'AG. MONTERRICO'
    WHEN lote BETWEEN 2281 AND 2300 THEN 'AG. ZARATE'
    WHEN lote BETWEEN 2301 AND 2320 THEN 'AG. SUCRE'
    WHEN lote BETWEEN 2321 AND 2340 THEN 'AG. CAVENECIA'
    WHEN lote BETWEEN 2341 AND 2360 THEN 'AG. HIGUERETA'
    WHEN lote BETWEEN 2361 AND 2380 THEN 'AG. SUNAD'
    WHEN lote BETWEEN 2381 AND 2400 THEN 'AG. SAN MARCOS'
    WHEN lote BETWEEN 2401 AND 2420 THEN 'AG. CHACARILLA'
    WHEN lote BETWEEN 2421 AND 2440 THEN 'AG. MORELLI'
    WHEN lote BETWEEN 2441 AND 2460 THEN 'AG. SANTA ANITA'
    WHEN lote BETWEEN 2461 AND 2480 THEN 'AG. JIRON PUNO'
    WHEN lote BETWEEN 2481 AND 2500 THEN 'AG. COMAS'
    WHEN lote BETWEEN 2501 AND 2520 THEN 'AG. PUENTE PIEDRA'
    WHEN lote BETWEEN 2521 AND 2540 THEN 'AG. CHORRILLOS'
    WHEN lote BETWEEN 2541 AND 2560 THEN 'AG. VILLA EL SALVADOR'
    WHEN lote BETWEEN 2561 AND 2580 THEN 'AG. GAMARRA'
    WHEN lote BETWEEN 2581 AND 2600 THEN 'AG. SALAVERRY'
    WHEN lote BETWEEN 2601 AND 2620 THEN 'AG. CPJ'
    WHEN lote BETWEEN 2621 AND 2640 THEN 'AG. EL POLO'
    WHEN lote BETWEEN 2641 AND 2660 THEN 'AG. RIVERA NAVARRETE'
    WHEN lote BETWEEN 2661 AND 2680 THEN 'AG. JESUS MARIA'
    WHEN lote BETWEEN 2681 AND 2700 THEN 'AG. DOS DE MAYO'
    WHEN lote BETWEEN 2701 AND 2720 THEN 'AG. SAN JUAN DE MIRAFLORES'
    WHEN lote BETWEEN 2721 AND 2740 THEN 'AG. FIORI'
    WHEN lote BETWEEN 2741 AND 2760 THEN 'AG. SAN MIGUEL'
    WHEN lote BETWEEN 3471 AND 3490 THEN 'AG. SCHELL'
    WHEN lote BETWEEN 5361 AND 5380 THEN 'AG. BASADRE'
    WHEN lote BETWEEN 3641 AND 3660 THEN 'AG. SALAVERRY 2'
    WHEN lote BETWEEN 2941 AND 2960 THEN 'AG. LA MOLINA'
    WHEN lote BETWEEN 3021 AND 3040 THEN 'AG. CHORRILLOS II'
    WHEN lote BETWEEN 3561 AND 3580 THEN 'AG. SAN HILARION'
    WHEN lote BETWEEN 3521 AND 3540 THEN 'AG. GRAU'
    WHEN lote BETWEEN 3041 AND 3060 THEN 'AG. CARSA BARRANCA'
    WHEN lote BETWEEN 3141 AND 3146 THEN 'AG. CARSA SAN JUAN DE MIRAFLOR'
    WHEN lote BETWEEN 3153 AND 3157 THEN 'AG. CARSA COMAS'
    WHEN lote BETWEEN 3159 AND 3164 THEN 'AG. CARSA JIRON DE LA UNION'
    WHEN lote BETWEEN 3177 AND 3182 THEN 'AG. CARSA VILLA EL SALVADOR'
    WHEN lote BETWEEN 3183 AND 3188 THEN 'AG. CARSA ATE'
    WHEN lote BETWEEN 3195 AND 3200 THEN 'AG. CARSA VENTANILLA'
    WHEN lote BETWEEN 3081 AND 3100 THEN 'AG. CARSA SAN JUAN DE LURIGANC'
    WHEN lote BETWEEN 3201 AND 3206 THEN 'AG. CARSA SAN MARTIN DE PORRES'
    WHEN lote BETWEEN 3207 AND 3212 THEN 'AG. CARSA HUARAL'
    WHEN lote BETWEEN 3213 AND 3218 THEN 'AG. CARSA HUACHO'
    WHEN lote BETWEEN 3219 AND 3224 THEN 'AG. CARSA CHOSICA'
    WHEN lote BETWEEN 3587 AND 3592 THEN 'AG. CARSA HUAYCAN'
    WHEN lote BETWEEN 2781 AND 2800 THEN ' AG. VILLA MARIA DEL TRIUNFO'
    WHEN lote BETWEEN 2761 AND 2780 THEN 'AG. PIURA'
    WHEN lote BETWEEN 2801 AND 2820 THEN 'AG. AGUAS VERDES'
    WHEN lote BETWEEN 2821 AND 2840 THEN 'AG. TUMBES'
    WHEN lote BETWEEN 2841 AND 2860 THEN 'AG. SULLANA'
    WHEN lote BETWEEN 2861 AND 2880 THEN 'AG. CAJAMARCA'
    WHEN lote BETWEEN 2961 AND 2980 THEN 'AG. HUANCAYO'
    WHEN lote BETWEEN 2981 AND 3000 THEN 'AG. HUARAZ'
    WHEN lote BETWEEN 3001 AND 3020 THEN 'AG. TACNA'
    WHEN lote BETWEEN 2881 AND 2900 THEN 'AG. CHICLAYO'
    WHEN lote BETWEEN 2921 AND 2940 THEN 'AG. TRUJILLO'
    WHEN lote BETWEEN 3101 AND 3120 THEN 'AG. CHIMBOTE'
    WHEN lote BETWEEN 3121 AND 3140 THEN 'AG. MALL VENTURA TRUJILLO'
    WHEN lote BETWEEN 3231 AND 3236 THEN 'AG. CARSA TUMBES'
    WHEN lote BETWEEN 3237 AND 3242 THEN 'AG. CARSA BOLIVAR'
    WHEN lote BETWEEN 3243 AND 3248 THEN 'AG. CARSA TRUJILLO 2'
    WHEN lote BETWEEN 3261 AND 3266 THEN 'AG. CARSA TARAPOTO'
    WHEN lote BETWEEN 3267 AND 3272 THEN 'AG. CARSA TALARA'
    WHEN lote BETWEEN 3273 AND 3278 THEN 'AG. CARSA TACNA'
    WHEN lote BETWEEN 3279 AND 3284 THEN 'AG. CARSA SULLANA'
    WHEN lote BETWEEN 3285 AND 3290 THEN 'AG. CARSA PUNO'
    WHEN lote BETWEEN 3291 AND 3296 THEN 'AG. CARSA PUCALLPA'
    WHEN lote BETWEEN 3297 AND 3302 THEN 'AG. CARSA PIURA GRAU'
    WHEN lote BETWEEN 3303 AND 3308 THEN 'AG. CARSA PEDRO RUIZ'
    WHEN lote BETWEEN 3315 AND 3320 THEN 'AG. CARSA PISCO'
    WHEN lote BETWEEN 3321 AND 3326 THEN 'AG. CARSA NAZCA'
    WHEN lote BETWEEN 5373 AND 5382 THEN 'AG. CARSA LA MERCED'
    WHEN lote BETWEEN 3339 AND 3344 THEN 'AG. CARSA JULIACA'
    WHEN lote BETWEEN 5383 AND 5392 THEN 'AG. CARSA JAEN'
    WHEN lote BETWEEN 3351 AND 3356 THEN 'AG. CARSA IQUITOS'
    WHEN lote BETWEEN 3357 AND 3362 THEN 'AG. CARSA IQUITOS 2'
    WHEN lote BETWEEN 3369 AND 3374 THEN 'AG. CARSA ICA'
    WHEN lote BETWEEN 3375 AND 3380 THEN 'AG. CARSA HUARAZ'
    WHEN lote BETWEEN 3381 AND 3386 THEN 'AG. CARSA HUANUCO'
    WHEN lote BETWEEN 3399 AND 3404 THEN 'AG. CARSA CHINCHA'
    WHEN lote BETWEEN 3405 AND 3410 THEN 'AG. CARSA CHIMBOTE'
    WHEN lote BETWEEN 3417 AND 3422 THEN 'AG. CARSA CAJAMARCA'
    WHEN lote BETWEEN 3423 AND 3428 THEN 'AG. CARSA AYACUCHO'
    WHEN lote BETWEEN 3429 AND 3434 THEN 'AG. CARSA MERCADERES'
    WHEN lote BETWEEN 3435 AND 3440 THEN 'AG. CARSA MEGA SAN JUAN'
    WHEN lote BETWEEN 3441 AND 3446 THEN 'AG. CARSA SANTO DOMINGO'
    WHEN lote BETWEEN 3451 AND 3470 THEN 'AG. HUANCAYO II'
    WHEN lote BETWEEN 3491 AND 3510 THEN 'AG. AREQUIPA'
    WHEN lote BETWEEN 3511 AND 3516 THEN 'AG. CARSA HUANCAYO II'
    WHEN lote BETWEEN 3541 AND 3546 THEN 'AG. CARSA YURIMAGUAS'
    WHEN lote BETWEEN 3547 AND 3550 THEN 'AG. CARSA PTO. MALDONADO'
    WHEN lote BETWEEN 3553 AND 3558 THEN 'AG. CARSA MOYOBAMBA'
    WHEN lote BETWEEN 3599 AND 3604 THEN 'AG. CARSA EL PORVENIR'
    WHEN lote BETWEEN 3611 AND 3616 THEN 'AG. CARSA JUANJUI'
    WHEN lote BETWEEN 3781 AND 3800 THEN 'AG. CHEPEN'
    WHEN lote BETWEEN 3661 AND 3666 THEN 'AG. CARSA CHULUCANAS'
    WHEN lote BETWEEN 3671 AND 3690 THEN 'AG. MOSHOQUEQUE'
    WHEN lote BETWEEN 3701 AND 3720 THEN 'AG. PUNO'
    WHEN lote BETWEEN 3721 AND 3740 THEN 'AG. CUSCO'
    WHEN lote BETWEEN 3761 AND 3780 THEN 'AG. ICA'
	--when lote = 6985 then 'DEPOSITO'
	when lote = 36 then 'AGENTE KASNET'
 
else 'OTRO'
 
end canal_trx,case when DebitoCredito=0 then 'SALIDA' else 'ENTRADA' end salida_entrada
 
 
from BFP_DATAWAREHOUSE..Fact_Sal_MovimientoContable
 
where cTiempo >= @ctiempo_inicial and cProducto in (1476,1477,1478,1479,1487,27172,29738,30046,
30049,1480,1481,1482,27170,29741,32993)

"""
 
 
# ============================================================================
# FUNCIÓN DE CARGA DE DATOS
# ============================================================================
 
def validar_y_cargar_datos(df, tabla_destino, engine, esquema='dbo'):
    """
    Valida que las columnas del DataFrame existan en la tabla SQL
    antes de iniciar la carga de datos.
    Args:
        df: DataFrame con los datos a cargar
        tabla_destino: Nombre de la tabla destino
        engine: SQLAlchemy engine
        esquema: Esquema de la tabla (default: 'dbo')
    Returns:
        bool: True si la carga fue exitosa, False en caso contrario
    """
    try:
        print(f"\n--- Iniciando proceso para tabla: {tabla_destino} ---")
        # 1. Obtener columnas reales de la base de datos
        inst = inspect(engine)
        columnas_sql = [c['name'] for c in inst.get_columns(tabla_destino, schema=esquema)]
        columnas_df = df.columns.tolist()
        # 2. Identificar discrepancias
        sobrantes_en_df = set(columnas_df) - set(columnas_sql)
        if sobrantes_en_df:
            print(f"❌ ERROR: El DataFrame tiene columnas que NO existen en la tabla SQL: {sobrantes_en_df}")
            print("Abortando carga para evitar errores de inserción.")
            return False
        print(f"✅ Validación exitosa: Las {len(columnas_df)} columnas coinciden.")
        # 3. Carga de datos
        print(f"Subiendo {len(df):,} registros...")
        with engine.begin() as connection:
            # Si quieres limpiar la tabla antes de subir, descomenta la línea de abajo:
            # connection.execute(text(f"TRUNCATE TABLE {esquema}.{tabla_destino}"))
            df.to_sql(
                name=tabla_destino,
                con=connection,
                schema=esquema,
                if_exists='append',
                index=False,
                chunksize=1000
            )
        print("🚀 ¡ÉXITO! Los datos se cargaron correctamente.")
        return True
    except Exception as e:
        print(f"❌ Error durante el proceso: {e}")
        return False
 
 
# ============================================================================
# PROCESO PRINCIPAL
# ============================================================================

def main():
    """Función principal que ejecuta todo el proceso"""
    print("=" * 60)
    print("INICIANDO PROCESO DE EXTRACCIÓN Y CARGA DE DATOS")
    print("=" * 60)

    # 1. Extraer datos de la fuente
    print("\n[1/3] Extrayendo datos desde BFP_DATAWAREHOUSE...")
    with engine_origen.begin() as conn:
        df = pd.read_sql(sql=SQL_RUM, con=conn)
    
    # --- VALIDACIÓN: ¿Está vacío? ---
    if df.empty:
        print("\n⚠️  ADVERTENCIA: No se encontraron datos en la consulta origen.")
        print("🛑 PROCESO DETENIDO: No hay información para cargar.")
        print("=" * 60)
        return  # Sale de la función y no ejecuta lo que sigue
    # --------------------------------

    print(f"✅ Datos extraídos correctamente: {len(df):,} filas")
    print("   Muestra de los primeros 3 registros:")
    print(df.head(3))

    # 2. Preparar datos (copia)
    print("\n[2/3] Preparando datos para carga...")
    df_sql = df.copy()
    print("✅ Datos preparados")

    # 3. Cargar datos a la tabla destino
    print("\n[3/3] Cargando datos a BFPMARKETING...")
    nombre_tabla = "trx_pref_pasivos"
    exito = validar_y_cargar_datos(df_sql, nombre_tabla, engine_destino)

    # 4. Resultado final
    print("\n" + "=" * 60)
    if exito:
        print("✅ PROCESO COMPLETADO CON ÉXITO")
    else:
        print("❌ PROCESO TERMINADO CON ERRORES")
    print("=" * 60)
    return exito

 
 
# ============================================================================
# EJECUCIÓN
# ============================================================================
 
if __name__ == "__main__":
    exito = main()
    if not exito:
        print("\nRevisa los mensajes de error arriba para más detalles.")