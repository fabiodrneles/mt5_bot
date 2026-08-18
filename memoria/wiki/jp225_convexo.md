# Motores Convexos

## JP225 (Índice Nikkei 225)
No dia 17 de Agosto de 2026, foi realizada uma pesquisa quantitativa abrangente (M5 e H1) nos ativos do MetaTrader 5 para identificar configurações convexas (perdas curtas e limitadas, lucros alongados e imensos) viáveis para saldos ultra pequenos (ex: $16.47). 

### Setup Campeão: 9.1 (H1)
* **Ativo**: JP225 (ou JPN225)
* **Margem exigida**: ~$0.43 (para 0.01 lote)
* **Resultado do Backtest**: 
  - +7636 pontos de lucro líquido em 3 meses.
  - Taxa de acerto (Winrate): ~37.4%.
* **Comportamento**: Extremamente direcional em gráficos maiores. Apesar da baixa taxa de acerto (normal em _trend following_), as tendências são tão fortes e duradouras que os lucros cobrem rapidamente as pequenas perdas das inversões de média móvel.
* **Configuração no Bot**: Roteado exclusivamente para o Setup 9.1 (`ASSET_SETUPS["JP225"] = ["9.1"]`), operando no horário da sessão Asiática (21:00 às 15:00 BRT).
