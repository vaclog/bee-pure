# AGENTS.md

## Alcance

Este directorio contiene procesos ETL de Ordenes de Venta. Para cambios nuevos, priorizar el ETL principal en `src/` y tratar los subdirectorios historicos por cliente como referencia legacy.

## Reglas

1. No modificar procesos legacy por cliente salvo pedido explicito.
2. No hardcodear credenciales, hosts, tokens ni rutas sensibles.
3. Toda configuracion sensible debe venir de variables de entorno o `.env` local no versionado.
4. Mantener el ETL nuevo chico, testeable y orientado al circuito del Dashboard OV.
5. No ejecutar SQL destructivo ni inserts reales sin contrato VKM confirmado.
6. Mantener `deposito_ov` y procesos legacy como referencia tecnica, no como fuente para copiar flujos completos.
