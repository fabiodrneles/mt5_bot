import os
import glob
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

# Constantes
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def train_for_dataset(csv_path):
    print(f"\n======================================")
    print(f"Iniciando treinamento para: {os.path.basename(csv_path)}")
    print(f"======================================")
    
    # Extrair o símbolo do nome do arquivo (ex: dataset_live_experience_HK50.csv -> HK50)
    filename = os.path.basename(csv_path)
    symbol = "UNKNOWN"
    if filename.startswith("dataset_live_experience_") and filename.endswith(".csv"):
        symbol = filename.replace("dataset_live_experience_", "").replace(".csv", "")
    elif filename == "dataset_massive.csv":
        symbol = "MASSIVE"
        
    print("Carregando dataset...")
    df = pd.read_csv(csv_path)
    
    if len(df) < 50:
        print(f"[SKIP] O dataset {filename} tem apenas {len(df)} amostras. Precisamos de pelo menos 50 para treinar com sentido.")
        return
        
    # Colunas que sabemos que não são numéricas ou não devem ser usadas no treino
    cols_to_drop = ['time', 'side', 'setup', 'pnl_pips', 'is_vetoed', 'veto_reason']
    
    # Nem todos os CSVs podem ter todas as colunas, então tentamos remover com cuidado
    drop_list = [c for c in cols_to_drop if c in df.columns]
    drop_list.append('result')  # sempre tem result
    
    X = df.drop(columns=drop_list)
    y = df['result']
    
    X.fillna(0, inplace=True)
    
    print(f"Total de features extraídas: {len(X.columns)}")
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print(f"Treinando com {len(X_train)} amostras. Testando com {len(X_test)} amostras.")
    
    # Treinar o Modelo XGBoost
    model = xgb.XGBClassifier(
        n_estimators=100,
        learning_rate=0.05,
        max_depth=4,
        random_state=42,
        eval_metric='logloss'
    )
    
    model.fit(X_train, y_train)
    
    # Avaliar o Modelo
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print("\n--- AVALIAÇÃO DO MODELO ---")
    print(f"Acurácia Geral: {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred, zero_division=0))
    
    # Salvar o Modelo
    out_json = os.path.join(ROOT_DIR, f"mt5bot_xgboost_{symbol}_v1.json")
    model.save_model(out_json)
    print(f"[SUCCESS] Modelo atualizado: {os.path.basename(out_json)}")

def main():
    # Procura por todos os arquivos de dataset na raiz do projeto
    search_patterns = [
        os.path.join(ROOT_DIR, "dataset_live_experience_*.csv"),
        os.path.join(ROOT_DIR, "data", "dataset_massive.csv")
    ]
    
    csv_files = []
    for pattern in search_patterns:
        csv_files.extend(glob.glob(pattern))
        
    if not csv_files:
        print(f"Nenhum arquivo CSV encontrado para treinamento.")
        return
        
    for f in csv_files:
        train_for_dataset(f)

if __name__ == "__main__":
    main()
