# -*- coding: utf-8 -*-
"""
Ejecuta el SQL (con tablas temporales globales) y exporta:
- archivo diario
- archivo mensual

Uso:
  python run_saldos.py --meses 0 --server SBIBFPR03 --database BFP_DATAWAREHOUSE
Opcionales:
  --output-dir "C:\\ruta\\salidas" --file-prefix "archivoSaldos_"
Si tienes un .env con OUTPUT_DIR y FILE_PREFIX, los toma automáticamente.
"""



import os
import sys
import argparse
import pandas as pd
import pyodbc

# Cargar .env si existe (opcional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ------------------------------------------------------
# 1) SQL COMPLETO (puedes pegar aquí tu script)
#    NOTA: más abajo reemplazamos &lt; &gt; &amp; por < > &
#    y el valor de @meses según el CLI.
# ------------------------------------------------------
SQL_SCRIPT_ORIGINAL = r"""
SET NOCOUNT ON;

---------------------------------------------------------
-- VARIABLES
---------------------------------------------------------
DECLARE @fecha DATE = DATEADD(DAY, -1, GETDATE());
DECLARE @meses INT = 0;
DECLARE @fecha_inicial DATE = EOMONTH(DATEADD(MONTH, -(@meses+1), DATEFROMPARTS(YEAR(@fecha), MONTH(@fecha), 1)));
-- DECLARE @tc FLOAT = 3.366;

---------------------------------------------------------
-- 1. TABLA TEMPORAL DE CLIENTE
---------------------------------------------------------
IF OBJECT_ID('tempdb..##temp_cliente1') IS NOT NULL DROP TABLE ##temp_cliente1;

SELECT DISTINCT 
    a.codigoclientebanco,
    a.cfuncionarionegocios,
    a.tipocliente,
    a.fechaapertura,
    b.Agencia,
    CASE WHEN cFuncionarioNegocios IN (4935,5016,5173,5708,5946) 
         THEN 'PATRIMONIAL' ELSE 'NO PATRIMONIAL' END AS patrimonial,
    c.Departamento,
    c.Agrupacion
INTO ##temp_cliente1
FROM cliente a
LEFT JOIN Funcionarios b ON a.cfuncionarionegocios = b.cFuncionario
LEFT JOIN agencia c ON b.cAgencia = c.cAgencia
WHERE a.tipocliente = 'persona natural'
  AND a.fechafinvigencia IS NULL;

---------------------------------------------------------
-- 2. BASE OPERATIVA
---------------------------------------------------------
IF OBJECT_ID('tempdb..##tmp_base_ope1') IS NOT NULL DROP TABLE ##tmp_base_ope1;

SELECT 
    FORMAT(fecha, 'yyyyMM') AS periodo,
    CAST(a12.fecha AS DATE) AS fecha,
    año, mes, dia, finmes,
    a11.codigoclientebanco,
    a11.numerooperacion,
    a15.codigomoneda,
    CASE 
        WHEN a16.CodigoProductoIBS IN('AHS3','AHS4') 
             AND (Producto ='SIN PRODUCTO' OR Producto IS NULL) 
             THEN 'Ahorros' 
        ELSE producto 
    END AS producto,
    saldoactual,
    a17.agencia,
    a17.Departamento,
    a17.Agrupacion,
    a17.patrimonial,
    -- ✅ Conversión a soles usando TipoCambio del mismo cTiempo solo si es USD
    CASE 
        WHEN a15.codigomoneda = 'usd' 
             THEN saldoactual * tcusd.TipoCambio 
        ELSE saldoactual 
    END AS saldo_sol
INTO ##tmp_base_ope1
FROM estadocontableoperacioncab a11
LEFT JOIN tiempo a12        ON a11.ctiempo = a12.ctiempo
LEFT JOIN producto a13      ON a11.cproducto = a13.cproducto
-- ❌ (opcional) puedes quitar este join si ya no lo usas en ningún lado:
-- LEFT JOIN tipocambio a14 ON a11.ctiempo=a14.ctiempo AND a11.cmoneda=a14.cmoneda
LEFT JOIN monedas a15       ON a11.cmoneda = a15.cmoneda
LEFT JOIN productoibs a16   ON a11.cproductoibs = a16.cproductoibs
LEFT JOIN ##temp_cliente1 a17 ON a11.codigoclientebanco = a17.codigoclientebanco
-- ✅ Nuevo join: TipoCambio USD (cMoneda='170') por mismo cTiempo
LEFT JOIN TipoCambio tcusd  ON a11.ctiempo = tcusd.ctiempo AND tcusd.cMoneda = '170'
WHERE fecha &gt;= @fecha_inicial
  AND a16.codigotipoproductoibs IN ('ahna','dpnp','dpgj','dpgn')
  AND a16.codigoproductoibs NOT IN ('ahds','ahdd')
  AND a17.tipocliente='persona natural';


---------------------------------------------------------
-- 3. TABLA FINAL ##final_ope1
---------------------------------------------------------
IF OBJECT_ID('tempdb..##final_ope1') IS NOT NULL DROP TABLE ##final_ope1;

CREATE TABLE ##final_ope1 (
    periodo INT,
    fecha DATE,
    dia INT,
    codigoclientebanco DECIMAL(18,0),
    numerooperacion DECIMAL(18,0),
    moneda NVARCHAR(255),
    producto NVARCHAR(255),
    saldo_inicial FLOAT,
    saldo_final FLOAT,
    crecimiento FLOAT,
    tipo NVARCHAR(255),
    agencia NVARCHAR(255),
    Departamento NVARCHAR(255),
    Agrupacion NVARCHAR(255),
    Patrimonial NVARCHAR(255)
);

---------------------------------------------------------
-- 4. GENERACIÓN DE FINAL_OPE1
---------------------------------------------------------
DECLARE @contador_i INT = 0;

WHILE (@contador_i &lt;= @meses)
BEGIN
    DECLARE @año INT = YEAR(DATEADD(MONTH, -@contador_i, DATEFROMPARTS(YEAR(@fecha), MONTH(@fecha), 1)));
    DECLARE @mes INT = MONTH(DATEADD(MONTH, -@contador_i, DATEFROMPARTS(YEAR(@fecha), MONTH(@fecha), 1)));
    DECLARE @cont INT = CASE 
                            WHEN @contador_i = 0 THEN DAY(@fecha) 
                            ELSE DAY(EOMONTH(DATEADD(MONTH, -@contador_i, DATEFROMPARTS(YEAR(@fecha), MONTH(@fecha),1)))) 
                        END;

    DECLARE @año_ant INT = YEAR(DATEADD(MONTH, -(@contador_i+1), DATEFROMPARTS(YEAR(@fecha), MONTH(@fecha),1)));
    DECLARE @mes_ant INT = MONTH(DATEADD(MONTH, -(@contador_i+1), DATEFROMPARTS(YEAR(@fecha), MONTH(@fecha),1)));

    IF OBJECT_ID('tempdb..##tmp_ope_ini1') IS NOT NULL DROP TABLE ##tmp_ope_ini1;

    SELECT *
    INTO ##tmp_ope_ini1
    FROM ##tmp_base_ope1
    WHERE año=@año_ant AND mes=@mes_ant AND finmes=1;

    IF OBJECT_ID('tempdb..##tmp_ope1') IS NOT NULL DROP TABLE ##tmp_ope1;

    SELECT *
    INTO ##tmp_ope1
    FROM ##tmp_base_ope1
    WHERE año=@año AND mes=@mes;

    DECLARE @contador INT = 1;

    WHILE (@contador &lt;= @cont)
    BEGIN
        INSERT INTO ##final_ope1
        SELECT
            (@año*100+@mes) AS periodo,
            CAST(CAST((@año*10000+@mes*100+@contador) AS NVARCHAR(8)) AS DATE) AS fecha,
            @contador AS dia,
            COALESCE(a.codigoclientebanco, b.codigoclientebanco),
            COALESCE(a.numerooperacion, b.numerooperacion),
            COALESCE(a.codigomoneda, b.codigomoneda),
            COALESCE(b.producto, a.producto),
            a.saldoactual AS saldo_inicial,
            b.saldoactual AS saldo_final,
            ISNULL(b.saldoactual,0) - ISNULL(a.saldoactual,0) AS crecimiento,
            CASE
                WHEN a.periodo IS NULL THEN 'venta'
                WHEN a.periodo IS NOT NULL AND a.saldoactual &lt; b.saldoactual THEN 'crecimiento'
                WHEN a.periodo IS NOT NULL AND a.saldoactual &lt;&gt; 0 AND a.saldoactual &gt; b.saldoactual THEN 'decrecimiento'
                WHEN b.periodo IS NULL THEN 'cancelacion'
                ELSE 'sin_variacion'
            END AS tipo,
            a.Agencia, a.Departamento, a.Agrupacion, a.patrimonial
        FROM ##tmp_ope_ini1 a
        FULL OUTER JOIN (SELECT * FROM ##tmp_ope1 WHERE dia=@contador) b 
               ON a.numerooperacion=b.numerooperacion;

        SET @contador = @contador + 1;
    END

    SET @contador_i = @contador_i + 1;
END;

---------------------------------------------------------
-- 5. RENOVACIONES DPF
---------------------------------------------------------
IF OBJECT_ID('tempdb..##base_dpf_cancelaciones1') IS NOT NULL DROP TABLE ##base_dpf_cancelaciones1;

SELECT 
    CONVERT(DATE, fecha, 103) AS fecha,
    codigoclientebanco,
    numerooperacion,
    codigomoneda,
    importe AS monto_cancelado,
    -- ✅ Si es USD, convierte con TipoCambio del mismo cTiempo
    CASE 
        WHEN c.codigomoneda = 'usd' 
             THEN importe * tcusd.TipoCambio 
        ELSE importe 
    END AS monto_cancelado_sol
INTO ##base_dpf_cancelaciones1
FROM fact_sal_movimientocontable a
LEFT JOIN tiempo b      ON a.ctiempo = b.ctiempo
LEFT JOIN monedas c     ON a.cmoneda = c.cmoneda
LEFT JOIN TipoCambio tcusd 
       ON a.ctiempo = tcusd.ctiempo 
      AND tcusd.cMoneda = '170'
WHERE fecha &gt; @fecha_inicial 
  AND fecha &lt;= @fecha
  AND debitocredito = 0
  AND narrativa LIKE '%canc%dep%plazo%'
  AND codigotransaccion = 'dd';


IF OBJECT_ID('tempdb..##base_dpf_aperturas1') IS NOT NULL DROP TABLE ##base_dpf_aperturas1;

SELECT 
    CONVERT(DATE, fecha, 103) AS fecha,
    codigoclientebanco,
    numerooperacion,
    codigomoneda,
    importe AS monto_apertura,
    -- ✅ Si es USD, convierte con TipoCambio del mismo cTiempo
    CASE 
        WHEN c.codigomoneda = 'usd' 
             THEN importe * tcusd.TipoCambio 
        ELSE importe 
    END AS monto_apertura_sol
INTO ##base_dpf_aperturas1
FROM fact_sal_movimientocontable a
LEFT JOIN tiempo b      ON a.ctiempo = b.ctiempo
LEFT JOIN monedas c     ON a.cmoneda = c.cmoneda
LEFT JOIN TipoCambio tcusd 
       ON a.ctiempo = tcusd.ctiempo 
      AND tcusd.cMoneda = '170'
WHERE fecha &gt; @fecha_inicial 
  AND fecha &lt;= @fecha
  AND debitocredito = 5
  AND narrativa LIKE '%apertura%contrato%'
  AND codigotransaccion = 'nd';


IF OBJECT_ID('tempdb..##base_dpf_renovaciones1') IS NOT NULL DROP TABLE ##base_dpf_renovaciones1;

SELECT a.fecha, a.codigoclientebanco, monto_apertura_sol, monto_cancelado_sol
INTO ##base_dpf_renovaciones1
FROM
    (SELECT fecha, codigoclientebanco, SUM(monto_apertura_sol) AS monto_apertura_sol
     FROM ##base_dpf_aperturas1 GROUP BY fecha, codigoclientebanco) a
INNER JOIN
    (SELECT fecha, codigoclientebanco, SUM(monto_cancelado_sol) AS monto_cancelado_sol
     FROM ##base_dpf_cancelaciones1 GROUP BY fecha, codigoclientebanco) b
ON a.codigoclientebanco=b.codigoclientebanco AND a.fecha=b.fecha
WHERE (monto_apertura_sol/monto_cancelado_sol) &gt;= 0.5;

IF OBJECT_ID('tempdb..##base_dpf_renovaciones_final1') IS NOT NULL DROP TABLE ##base_dpf_renovaciones_final1;

SELECT DISTINCT *, 'renovacion' AS cat
INTO ##base_dpf_renovaciones_final1
FROM (
    SELECT DISTINCT a.numerooperacion
    FROM ##base_dpf_aperturas1 a
    INNER JOIN ##base_dpf_renovaciones1 b ON a.codigoclientebanco=b.codigoclientebanco AND a.fecha=b.fecha
    UNION ALL
    SELECT DISTINCT a.numerooperacion
    FROM ##base_dpf_cancelaciones1 a
    INNER JOIN ##base_dpf_renovaciones1 b ON a.codigoclientebanco=b.codigoclientebanco AND a.fecha=b.fecha
) a;

---------------------------------------------------------
-- 6. TABLA FINAL ##tmp_saldos_ope2
---------------------------------------------------------
IF OBJECT_ID('tempdb..##tmp_saldos_ope2') IS NOT NULL DROP TABLE ##tmp_saldos_ope2;

SELECT 
    periodo, dia, producto, moneda, agencia, cat, valor,
    Departamento, Agrupacion, patrimonial,
    inicial_mas_1m, final_mas_1m
INTO ##tmp_saldos_ope2
FROM (
    SELECT 
        x.periodo, x.dia, producto, moneda, agencia,
        Departamento, Agrupacion, Patrimonial,
        inicial_mas_1m, final_mas_1m,
        SUM(saldo_inicial) AS saldo_inicial,
        SUM(saldo_final) AS saldo_final,
        SUM(venta) AS venta,
        SUM(venta_renov) AS venta_renov,
        SUM(crecimiento) AS crecimiento,
        SUM(decrecimiento) AS decrecimiento,
        SUM(cancelacion) AS cancelacion,
        SUM(cancelacion_renov) AS cancelacion_renov
    FROM (
        SELECT 
            periodo, dia, producto, moneda,
            a.agencia, a.Departamento, a.Agrupacion, a.Patrimonial,
            a.codigoclientebanco,
            CASE WHEN SUM(saldo_inicial) &gt; 1000000 THEN 1 ELSE 0 END AS inicial_mas_1m,
            CASE WHEN SUM(saldo_final) &gt; 1000000 THEN 1 ELSE 0 END AS final_mas_1m,
            SUM(saldo_inicial) AS saldo_inicial,
            SUM(saldo_final) AS saldo_final,
            SUM(CASE WHEN tipo2='venta' THEN crecimiento END) AS venta,
            SUM(CASE WHEN tipo2='venta_renovacion' THEN crecimiento END) AS venta_renov,
            SUM(CASE WHEN tipo2='crecimiento' THEN crecimiento END) AS crecimiento,
            SUM(CASE WHEN tipo2='decrecimiento' THEN crecimiento END) AS decrecimiento,
            SUM(CASE WHEN tipo2='cancelacion' THEN crecimiento END) AS cancelacion,
            SUM(CASE WHEN tipo2='cancelacion_renovacion' THEN crecimiento END) AS cancelacion_renov
        FROM (
            SELECT 
                a.*, 
                CASE WHEN b.cat IS NULL THEN a.tipo 
                     ELSE a.tipo + '_' + b.cat END AS tipo2
            FROM ##final_ope1 a
            LEFT JOIN ##base_dpf_renovaciones_final1 b 
                   ON a.numerooperacion=b.numerooperacion 
                  AND a.tipo IN ('venta','cancelacion')
        ) a
        GROUP BY producto, moneda, dia, periodo, 
                 a.agencia, a.Departamento, a.Agrupacion, a.Patrimonial, 
                 a.codigoclientebanco
    ) x
    GROUP BY producto, moneda, dia, periodo, agencia, 
             Departamento, Agrupacion, Patrimonial, 
             inicial_mas_1m, final_mas_1m
) a
UNPIVOT (
    valor FOR cat IN (
        [saldo_inicial],[saldo_final],[venta],[venta_renov],
        [crecimiento],[decrecimiento],[cancelacion],[cancelacion_renov]
    )
) b
ORDER BY periodo, dia, agencia;
"""

# ------------------------------------------------------
# 2) Funciones utilitarias
# ------------------------------------------------------
def build_conn_str(server, database, trusted=True, driver="ODBC Driver 17 for SQL Server",
                   encrypt="yes", trust_server_cert="yes", username=None, password=None):
    if trusted:
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"Encrypt={encrypt};"
            f"TrustServerCertificate={trust_server_cert};"
        )
    else:
        if not username or not password:
            raise ValueError("Debe proveer username y password si Trusted_Connection=no")
        return (
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};PWD={password};"
            f"Encrypt={encrypt};"
            f"TrustServerCertificate={trust_server_cert};"
        )

def limpiar_html_entities(sql_text: str) -> str:
    return (sql_text
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
            )

def preparar_sql(sql_text: str, meses: int) -> str:
    """
    Inserta el valor de @meses deseado.
    Se asume que existe la línea 'DECLARE @meses INT = 0;'
    """
    sql_text = limpiar_html_entities(sql_text)
    return sql_text.replace("DECLARE @meses INT = 0;", f"DECLARE @meses INT = {meses};")

def exportar_saldos_completo(df, output_dir, file_prefix="archivoSaldos_", 
                             columna_periodo='periodo', columna_dia='dia'):
    os.makedirs(output_dir, exist_ok=True)

    # 1) Procesamiento de fecha
    df_proc = df.copy()
    df_proc['fecha_str'] = df_proc[columna_periodo].astype(str) + df_proc[columna_dia].astype(str).str.zfill(2)
    df_proc['fecha'] = pd.to_datetime(df_proc['fecha_str'], format='%Y%m%d')

    # 2) Rutas
    fecha_max_str = df_proc['fecha'].max().strftime('%Y%m%d')  # Ej: 20260120
    periodo_str = str(df_proc[columna_periodo].max())          # Ej: 202601

    ruta_diaria = os.path.join(output_dir, f"{file_prefix}{fecha_max_str}.xlsx")
    ruta_mensual = os.path.join(output_dir, f"{file_prefix}{periodo_str}.xlsx")
    ## ruta_consolidado = os.path.join(output_dir, f"{file_prefix}CONSOLIDADO_GENERAL.xlsx")

    # 3) Guardar Diario y Mensual
    df_export = df_proc.drop(columns=['fecha_str'])
    with pd.ExcelWriter(ruta_diaria, engine='openpyxl') as w:
        df_export.to_excel(w, index=False)
    with pd.ExcelWriter(ruta_mensual, engine='openpyxl') as w:
        df_export.to_excel(w, index=False)

    print(f'✅ Archivo diario: {ruta_diaria}')
    print(f'🔄 Archivo mensual actualizado: {ruta_mensual}')

    return ruta_diaria, ruta_mensual

# ------------------------------------------------------
# 3) Main
# ------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Ejecuta el query de saldos y exporta resultados.")
    parser.add_argument("--server", default="SBIBFPR03", help="Servidor SQL Server")
    parser.add_argument("--database", default="BFP_DATAWAREHOUSE", help="Base de datos")
    parser.add_argument("--driver", default="ODBC Driver 17 for SQL Server", help="Driver ODBC")
    parser.add_argument("--trusted", action="store_true", default=True, help="Usar Trusted_Connection")
    parser.add_argument("--no-trusted", dest="trusted", action="store_false", help="No usar Trusted_Connection")
    parser.add_argument("--username", help="Usuario SQL (si no es trusted)")
    parser.add_argument("--password", help="Password SQL (si no es trusted)")
    parser.add_argument("--meses", type=int, default=0, help="Meses hacia atrás a procesar (0 = mes actual hasta @fecha)")
    parser.add_argument("--output-dir", default=os.getenv("OUTPUT_DIR", os.getcwd()), help="Carpeta de salida")
    parser.add_argument("--file-prefix", default=os.getenv("FILE_PREFIX", "archivoSaldos_"), help="Prefijo de archivos de salida")
    args = parser.parse_args()

    # Construir cadena de conexión
    conn_str = build_conn_str(
        server=args.server,
        database=args.database,
        trusted=args.trusted,
        driver=args.driver,
        username=args.username,
        password=args.password
    )

    # Preparar SQL
    sql_script = preparar_sql(SQL_SCRIPT_ORIGINAL, meses=args.meses)

    print("🟦 Conectando a SQL Server...")
    with pyodbc.connect(conn_str, autocommit=True) as conn:
        print("🟦 Ejecutando script SQL con tablas temporales...")
        with conn.cursor() as cursor:
            cursor.execute(sql_script)
            # Evitar HY000 por resultsets previos
            while cursor.nextset():
                pass

        print("🟦 Leyendo SELECT final desde ##tmp_saldos_ope2 ...")
        query_final = """
            SELECT 
                periodo, dia, producto,
                CASE WHEN agencia IS NULL THEN 'NO DEFINIDA' ELSE agencia END AS agencia,
                Departamento, Agrupacion, moneda, cat, valor,
                CASE WHEN Patrimonial IS NULL AND agencia IS NULL THEN 'VENTA' ELSE Patrimonial END AS patrimonial,
                inicial_mas_1m, final_mas_1m
            FROM ##tmp_saldos_ope2;
        """
        df_raw = pd.read_sql(query_final, conn)

    if df_raw.empty:
        print("⚠️ No se obtuvieron filas del SELECT final. Revisa filtros/fechas.")
        sys.exit(0)

    print(f"🔢 Registros obtenidos: {len(df_raw):,}")
    rutas = exportar_saldos_completo(
        df=df_raw,
        output_dir=args.output_dir,
        file_prefix=args.file_prefix
    )

    diario, mensual = rutas
    print(f"   • Diario: {diario}")
    print(f"   • Mensual: {mensual}")

if __name__ == "__main__":
    main()